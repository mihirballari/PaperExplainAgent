import json
import re
from typing import List, Dict, Any, Union, Optional
import io
import os
import base64
from PIL import Image
import mimetypes
import litellm
from litellm import completion, completion_cost
from dotenv import load_dotenv

load_dotenv()

class LiteLLMWrapper:
    """Wrapper for LiteLLM to support multiple models and logging"""
    
    def __init__(
        self,
        model_name: str = "deepseek/deepseek-chat", # Example default
        temperature: float = 0.7,
        print_cost: bool = False,
        verbose: bool = False,
        use_langfuse: bool = True,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.print_cost = print_cost
        self.verbose = verbose
        self.accumulated_cost = 0

        if self.verbose:
            os.environ['LITELLM_LOG'] = 'DEBUG'
        
        if use_langfuse:
            litellm.success_callback = ["langfuse"]
            litellm.failure_callback = ["langfuse"]

    def _encode_file(self, file_path: Union[str, Image.Image]) -> str:
        if isinstance(file_path, Image.Image):
            buffered = io.BytesIO()
            file_path.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        else:
            with open(file_path, "rb") as file:
                return base64.b64encode(file.read()).decode("utf-8")

    def _get_mime_type(self, file_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            raise ValueError(f"Unsupported file type: {file_path}")
        return mime_type

    def __call__(self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
        if metadata is None:
            print("No metadata provided, using empty metadata")
            metadata = {}
        metadata["trace_name"] = f"litellm-completion-{self.model_name}"
        
        formatted_messages = []
        for msg in messages:
            if msg["type"] == "text":
                formatted_messages.append({
                    "role": "user",
                    "content": [{"type": "text", "text": msg["content"]}]
                })
            elif msg["type"] in ["image", "audio", "video"]:
                if isinstance(msg["content"], Image.Image) or os.path.isfile(msg["content"]):
                    try:
                        if isinstance(msg["content"], Image.Image):
                            mime_type = "image/png"
                        else:
                            mime_type = self._get_mime_type(msg["content"])
                        base64_data = self._encode_file(msg["content"])
                        data_url = f"data:{mime_type};base64,{base64_data}"
                    except ValueError as e:
                        print(f"Error processing file {msg['content']}: {e}")
                        continue
                else:
                    data_url = msg["content"]
                
                # --- MODIFIED LOGIC START ---
                if "gemini" in self.model_name:
                    # Gemini Format
                    formatted_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": data_url
                            }
                        ]
                    })
                elif "gpt" in self.model_name or "deepseek" in self.model_name:
                    # GPT & DeepSeek Format (OpenAI Compatible)
                    if msg["type"] == "image":
                        formatted_messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": data_url,
                                        "detail": "high"  
                                    }
                                }
                            ]
                        })
                    else:
                        raise ValueError(f"For {self.model_name}, only text and image inferencing are supported")
                else:
                    raise ValueError("Only support Gemini, GPT, and DeepSeek for Multimodal capability now")
                # --- MODIFIED LOGIC END ---

        try:
            if "deepseek" in self.model_name:
                response = completion(
                    model=self.model_name,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    metadata=metadata,
                    max_retries=3, # Lowered from 99 for sanity
                    #api_base="https://api.deepseek.com/v3.2_speciale_expires_on_20251215",
                )
                if self.print_cost:
                    cost = completion_cost(completion_response=response)
                    self.accumulated_cost += cost
                    print(f"Accumulated Cost: ${self.accumulated_cost:.10f}")

                content = response.choices[0].message.content
                return content
            
            response = completion(
                model=self.model_name,
                messages=formatted_messages,
                temperature=self.temperature,
                metadata=metadata,
                max_retries=3 # Lowered from 99 for sanity
            )
            if self.print_cost:
                cost = completion_cost(completion_response=response)
                self.accumulated_cost += cost
                print(f"Accumulated Cost: ${self.accumulated_cost:.10f}")
                
            content = response.choices[0].message.content
            return content
        
        except Exception as e:
            print(f"Error in model completion: {e}")
            return str(e)

if __name__ == "__main__":
    pass