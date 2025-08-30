from langchain_community.agent_toolkits.openapi.spec import reduce_openapi_spec
import yaml

def get_spec(filename: str):
    with open(filename) as f:
        raw_openai_api_spec = yaml.load(f, Loader=yaml.Loader)
    openai_api_spec = reduce_openapi_spec(raw_openai_api_spec)
    return openai_api_spec