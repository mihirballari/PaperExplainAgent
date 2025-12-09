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
        model_name: str = "gpt-4-vision-preview",
        temperature: float = 0.7,
        print_cost: bool = False,
        verbose: bool = False,
        use_langfuse: bool = True,
    ):
        """
        Initialize the LiteLLM wrapper
        
        Args:
            model_name: Name of the model (e.g. "azure/gpt-4", "deepseek/deepseek-chat")
            temperature: Temperature for completion (ignored for o-series models)
            print_cost: Whether to print the cost of the completion
            verbose: Whether to print verbose output
            use_langfuse: Whether to enable Langfuse logging
        """
        self.model_name = model_name
        self.temperature = temperature
        self.print_cost = print_cost
        self.verbose = verbose
        self.accumulated_cost = 0

        if self.verbose:
            os.environ['LITELLM_LOG'] = 'DEBUG'
        
        # Set langfuse callback only if enabled
        if use_langfuse:
            litellm.success_callback = ["langfuse"]
            litellm.failure_callback = ["langfuse"]

    def _encode_file(self, file_path: Union[str, Image.Image]) -> str:
        """Encode local file or PIL Image to base64 string"""
        if isinstance(file_path, Image.Image):
            buffered = io.BytesIO()
            file_path.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        else:
            with open(file_path, "rb") as file:
                return base64.b64encode(file.read()).decode("utf-8")

    def _get_mime_type(self, file_path: str) -> str:
        """Get the MIME type of a file based on its extension"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            # Fallback for common image types if automatic detection fails
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return f"image/{file_path.split('.')[-1]}"
            raise ValueError(f"Unsupported file type: {file_path}")
        return mime_type

    def __call__(self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process messages and return completion
        
        Args:
            messages: List of message dictionaries with 'type' and 'content' keys
            metadata: Optional metadata to pass to litellm completion
        """
        if metadata is None:
            if self.verbose: print("No metadata provided, using empty metadata")
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
                # 1. Handle File/Image Processing
                if isinstance(msg["content"], Image.Image) or (isinstance(msg["content"], str) and os.path.isfile(msg["content"])):
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
                    # Assume it's already a URL or base64 string
                    data_url = msg["content"]
                
                # 2. Format Message based on Model Family
                if "gemini" in self.model_name.lower():
                    # Google Gemini Format
                    formatted_messages.append({
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": data_url}
                        ]
                    })
                else:
                    # Universal Format (Works for GPT, Claude, DeepSeek, etc.)
                    # We default to this standard instead of raising an error.
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

        try:
            # Check for OpenAI o-series (reasoning models)
            # These require temperature=None (or 1.0 fixed) and support reasoning_effort
            is_o_series = (re.match(r"^o\d+.*$", self.model_name) or 
                           re.match(r"^openai/o.*$", self.model_name))
            
            completion_kwargs = {
                "model": self.model_name,
                "messages": formatted_messages,
                "metadata": metadata,
                "max_retries": 3 # Reduced from 99 to be safer
            }

            if is_o_series:
                # o1/o3 models do not support temperature (must be default/None)
                # They support reasoning_effort="low"|"medium"|"high"
                completion_kwargs["reasoning_effort"] = "medium"
            else:
                # Standard models use the temperature setting
                completion_kwargs["temperature"] = self.temperature

            response = completion(**completion_kwargs)

            if self.print_cost:
                cost = completion_cost(completion_response=response)
                self.accumulated_cost += cost
                print(f"Accumulated Cost: ${self.accumulated_cost:.6f}")
                
            content = response.choices[0].message.content
            
            if content is None:
                print(f"Got null response from model. Full response: {response}")
                return ""
                
            return content
        
        except Exception as e:
            print(f"Error in model completion: {e}")
            return str(e)
        
if __name__ == "__main__":
    pass