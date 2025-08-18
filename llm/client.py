from __future__ import annotations
import os
import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        """
        Initialize LLM client with OpenAI configuration.
        
        Args:
            model: OpenAI model name to use
            temperature: Sampling temperature for responses
        """
        api_key =  os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set the 'OPENAI_API_KEY' environment variable."
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str, schema: Type[T]) -> T:
        """
        Enforce a structured JSON output that must validate against `schema`.
        Returns a Pydantic model instance (typed).
        """
        # Pydantic v2 JSON Schema with strict mode requirements
        json_schema = schema.model_json_schema()
        
        # Add additionalProperties: false for OpenAI strict mode
        def add_additional_properties_false(obj):
            if isinstance(obj, dict):
                if "type" in obj and obj["type"] == "object":
                    obj["additionalProperties"] = False
                for value in obj.values():
                    add_additional_properties_false(value)
            elif isinstance(obj, list):
                for item in obj:
                    add_additional_properties_false(item)
        
        add_additional_properties_false(json_schema)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.0,  
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,        # enforce adherence to schema
                    "schema": json_schema, 
                },
            },
        )

        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            # Surface a clean error; caller can decide fallback (e.g., retry or S2 route)
            raise RuntimeError(f"Structured output validation failed: {e}") from e
