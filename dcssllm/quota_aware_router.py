
import logging
from datetime import time

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import BaseMessage, BaseMessageChunk
from typing import (
    List, Any, Tuple, Dict, Iterator, AsyncIterator, Optional, Sequence, 
    Callable, Literal, Union,
)
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from dcssllm.non_consuming_rate_limiter import NonConsumingRateLimiter

logger = logging.getLogger(__name__)

class QuotaAwareRouter(BaseChatModel):
    """
    A model that routes requests to the best model available based on the rate limiters.
    """

    """
    A list of tuples, where each tuple contains a language model and a list of rate limiters.
    The first model in the list where all the rate limiters are not exceeded is the active model.
    """
    _models: List[Tuple[BaseChatModel, List[NonConsumingRateLimiter]]]
    _next_selected_model: Optional[BaseChatModel] = None

    def __init__(self, models: List[Tuple[BaseChatModel, List[NonConsumingRateLimiter]]]):
        super().__init__()
        self._models = models
        
    def get_active_model(self, consume: bool = False) -> BaseChatModel:
        """
        Get the active model. This will bump the rate limiters for the returned model.

        Multiple calls to this method may happen before we actually use the model, so
        there is logic to determine what the next model should be.
        """

        # If we have already chosen which model to use next, use that.
        if self._next_selected_model is not None:
            ret = self._next_selected_model
            if consume:
                self._next_selected_model = None
            return ret

        # Try to decide which model to use next.
        while True:
            for model, limiters in self._models:
                # If there's only one limiter, we can just use that and avoid the race condition.
                if len(limiters) <= 1:
                    if len(limiters) == 0 or limiters[0].acquire():
                        if not consume:
                            # We're not consuming, so we can use this model next.
                            self._next_selected_model = model
                        return model
                else:
                    # Check if all the rate limiters are not exceeded.
                    if not all(limiter.can_consume() for limiter in limiters):
                        continue
                    # Eagerly consume the quota for this model.
                    for limiter in limiters:
                        limiter.acquire()

                    if not consume:
                        # We're not consuming, so we can use this model next.
                        self._next_selected_model = model
                    return model
            time.sleep(0.1)

    def bind_tools(
        self, 
        tools: Sequence[
            Union[Dict[str, Any], type, Callable, BaseTool]
        ],
        *,
        tool_choice: Optional[Union[str, Literal["any"]]] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """
        Bind the tools to all the models as we don't know which model will be used.
        Runs only once during initialization.
        """
        return QuotaAwareRouter(
            [
                (model.bind_tools(tools, tool_choice=tool_choice, **kwargs), limiters) 
                for model, limiters in self._models
            ]
        )
    
    def with_structured_output(
        self,
        schema: Union[Dict, type],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, Union[Dict, BaseModel]]:
        return QuotaAwareRouter(
            [
                (model.with_structured_output(schema, include_raw=include_raw, **kwargs), limiters) 
                for model, limiters in self._models
            ]
        )

    #
    # We're doing some hacky stuff here and disobeying the contract of BaseChatModel.
    #
    # Instead of overriding the official methods, we're going to override the actual
    # invocation methods. This helps ensure as much logic is delegated to the underlying
    # model as possible.
    #
    def invoke(self, *args, **kwargs: Any) -> BaseMessage:
        return self.get_active_model(consume=True).invoke(*args, **kwargs)

    def ainvoke(self, *args, **kwargs: Any) -> BaseMessage:
        return self.get_active_model(consume=True).ainvoke(*args, **kwargs)
    
    def stream(self, *args, **kwargs: Any) -> Iterator[BaseMessageChunk]:
        return self.get_active_model(consume=True).stream(*args, **kwargs)

    def astream(self, *args, **kwargs: Any) -> AsyncIterator[BaseMessageChunk]:
        return self.get_active_model(consume=True).astream(*args, **kwargs)
    
    def batch(self, *args, **kwargs: Any) -> List[BaseMessage]:
        return self.get_active_model(consume=True).batch(*args, **kwargs)

    def abatch(self, *args, **kwargs: Any) -> List[BaseMessage]:
        return self.get_active_model(consume=True).abatch(*args, **kwargs)
    
    def batch_as_completed(self, *args, **kwargs: Any) -> Iterator[Tuple[int, Union[BaseMessage, Exception]]]:
        return self.get_active_model(consume=True).batch_as_completed(*args, **kwargs)

    def abatch_as_completed(self, *args, **kwargs: Any) -> AsyncIterator[Tuple[int, Union[BaseMessage, Exception]]]:
        return self.get_active_model(consume=True).abatch_as_completed(*args, **kwargs) 

    #
    # These are needed but not technically used.
    #    
    def _generate(self, messages: List[BaseMessage], **kwargs: Any) -> BaseMessage:
        logger.warn("Use of _generate is not supposed to happen")
        return self.get_active_model(consume=True)._generate(messages, **kwargs)

    def _stream(self, messages: List[BaseMessage], **kwargs: Any) -> Iterator[BaseMessageChunk]:
        logger.warn("Use of _stream is not supposed to happen")
        return self.get_active_model(consume=True)._stream(messages, **kwargs)
    
    def _agenerate(self, messages: List[BaseMessage], **kwargs: Any) -> AsyncIterator[BaseMessageChunk]:
        logger.warn("Use of _agenerate is not supposed to happen")
        return self.get_active_model(consume=True)._agenerate(messages, **kwargs)
    
    def _astream(self, messages: List[BaseMessage], **kwargs: Any) -> AsyncIterator[BaseMessageChunk]:
        logger.warn("Use of _astream is not supposed to happen")
        return self.get_active_model(consume=True)._astream(messages, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        logger.warn("Use of _llm_type is not supposed to happen")
        return self.get_active_model()._llm_type
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        logger.warn("Use of _llm_type is not supposed to happen")
        return self.get_active_model()._identifying_params

