import os

class DeepseekWraper:
    def __init__(
        self,
        model_name: str,
        temperature: float,
        print_cost: bool = False,
        verbose: bool = False,
        use_langfuse: bool = False
    ):
        self.model_name = model_name.split('/')[-1] if '/' in model_name else model_name
        self.temperature = temperature
        self.print_cost = print_cost
        self.verbose = verbose
        self.accumulated_cost = 0

        api_key = os.getenv("GEMINI_API_KEY")