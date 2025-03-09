import boto3
import json
from typing import Optional, List
from langchain.llms.base import BaseLanguageModel
from langchain.schema import BaseMessage, HumanMessage
from langchain_aws import ChatBedrockConverse

class ConcreteBedrockChatWrapper(BaseLanguageModel):
    """
    A concrete wrapper for Amazon Bedrock Chat that implements the required methods
    by delegating to an inner ChatBedrockConverse instance.
    """
    def __init__(self, client, model: str, temperature: float = 0.7):
        self.inner_llm = ChatBedrockConverse(client=client, model=model, temperature=temperature)
        self.temperature = temperature
        self.model = model

    def predict_messages(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> str:
        # Delegate to the inner LLM's invoke method.
        return self.inner_llm.invoke(messages)

    def predict(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # Wrap the prompt in a HumanMessage and delegate.
        messages = [HumanMessage(content=prompt)]
        return self.predict_messages(messages, stop=stop)

    async def apredict_messages(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> str:
        return self.predict_messages(messages, stop=stop)

    async def apredict(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        return self.predict(prompt, stop=stop)

    def generate_prompt(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        # Simply return the messages as the "prompt"
        return messages

    async def agenerate_prompt(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        return self.generate_prompt(messages)

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model, "temperature": self.temperature}

    @property
    def _llm_type(self) -> str:
        return "amazon_bedrock"
