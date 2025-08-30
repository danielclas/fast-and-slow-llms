import argparse
from pathlib import Path
from typing import Dict
from pydantic import BaseModel
from io_utils import read_jsonl
from llm.base.base_agent import BaseAgent
from llm.controller.controller import Controller
from llm.llm_router import LLMAgentsRouter, SingleAgentRouter
from llm.s1.s1_agent import AgentS1
from llm.s2.s2_agent import AgentS2
from llm.client import LLMClient
from llm.tools import load_openapi_specs, format_api_context_for_agent
import json
from datetime import datetime 

class EmailRecord(BaseModel):
    id: str
    email_text: str

def process_dataset(
    dataset_path: str,
    run_dir: str,
    controller: Controller,
    agents: Dict[str, BaseAgent],
    run_metadata: Dict,
) -> None:
    """
    Process the entire dataset at once, writing enriched results to merged.jsonl
    """
    out_merged = str(Path(run_dir) / "merged.jsonl")
    
    # Ensure output directory exists
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    
    # Clear output file if it exists (overwrite mode)
    if Path(out_merged).exists():
        Path(out_merged).unlink()
    
    # Write metadata as first line
    metadata_record = {
        "type": "metadata",
        "run_config": run_metadata
    }
    with open(out_merged, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata_record, ensure_ascii=False) + "\n")

    processed = 0
    for sample_data in read_jsonl(dataset_path):
        try:
            # Validate and parse the email record
            sample = EmailRecord.model_validate(sample_data)
        except Exception as e:
            print(f"Warning: Invalid email record format: {e}")
            print(f"Skipping: {sample_data}")
            continue

        email_text = sample.email_text
        
        # Get routing decision
        route_decision = controller.route(email_text)
        route = route_decision.route

        # Select agent based on route
        agent = agents.get(route) or agents.get("S2") or agents.get("S1")
        raw_response = agent.run(email_text)

        try:
            agent_response = json.loads(raw_response)
            
            # Extract structured components
            action_sequence = agent_response.get("action_sequence", [])
            reasoning = agent_response.get("reasoning", "")
            agent_confidence = agent_response.get("confidence", 0.0)
            
            # Build enriched response with both raw and parsed data
            enriched = {
                **sample.model_dump(),
                "run": {
                    "route_pred": route,
                    "route_decision": {
                        "route": route_decision.route,
                        "reasons": route_decision.reasons,

                        "confidence": route_decision.confidence
                    },
                    "agent": {
                        "name": agent.__class__.__name__,
                        "raw": raw_response,  # Original JSON string
                        "parsed": {
                            "action_sequence": action_sequence,
                            "reasoning": reasoning,
                            "confidence": agent_confidence,
                            "num_actions": len(action_sequence)
                        }
                    },
                    # Result added when grading
                    "result": {
                        "grade": "",
                    }
                }
            }
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback if parsing fails
            print(f"Warning: Failed to parse agent response for {sample.id}: {e}")
            enriched = {
                **sample.model_dump(),
                "run": {
                    "route_pred": route,
                    "route_decision": {
                        "route": route_decision.route,
                        "reasons": route_decision.reasons,

                        "confidence": route_decision.confidence
                    },
                    "agent": {
                        "name": agent.__class__.__name__,
                        "raw": raw_response,
                        "parsed": None,
                        "parse_error": str(e)
                    }
                }
            }
        
        # Write result
        with open(out_merged, "a", encoding="utf-8") as f:
            f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
        
        processed += 1
        if processed % 10 == 0:
            print(f"Processed {processed} samples...")

    print(f"Completed processing {processed} samples. Results written to {out_merged}")


def main():
    ap = argparse.ArgumentParser(description="Process email dataset through LLM router and agents")
    ap.add_argument("--dataset", required=True, help="Path to input JSONL dataset")
    ap.add_argument("--run-dir", required=True, help="Output directory for results")
    ap.add_argument("--agent", choices=["S1", "S2"], help="Force routing to specific agent for baseline testing")
    ap.add_argument("--confidence-threshold", type=float, default=0.5, 
                    help="Minimum confidence threshold for routing decisions (default: 0.5)")
    ap.add_argument("--s1-model", default="gpt-4o-mini", 
                    help="LLM model to use for S1 agent (default: gpt-4o-mini)")
    ap.add_argument("--s2-model", default="gpt-4o", 
                    help="LLM model to use for S2 agent (default: gpt-4o)")
    args = ap.parse_args()

    # Initialize router based on arguments
    if args.agent:
        # Baseline mode: always route to specified agent
        router = SingleAgentRouter(args.agent)
        print(f"Running in baseline mode: all emails routed to {args.agent}")
        print(f"Using {args.s1_model if args.agent == "S1" else args.s2_model} for ${args.agent} agent")
    else:
        # Intelligent routing mode
        router_llm_client = LLMClient()
        router = LLMAgentsRouter(llm=router_llm_client)
        print("Running in intelligent routing mode")
        print(f"Using {args.s1_model} for S1 agent and {args.s2_model} for S2 agent")
    
    controller = Controller(router=router, confidence_threshold=args.confidence_threshold)
    print(f"Using confidence threshold: {args.confidence_threshold}")
    
    # Load OpenAPI specifications for agents
    print("Loading OpenAPI specifications...")
    api_context = load_openapi_specs()
    api_context_string = format_api_context_for_agent(api_context)
    print(f"Loaded API context with {len(api_context.get('summary', []))} total endpoints")
    
    # Create separate LLM clients for each agent with their preferred models
    s1_llm_client = LLMClient(model=args.s1_model)  # Model for S1
    s2_llm_client = LLMClient(model=args.s2_model)  # Model for S2
    
    agents = {
        "S1": AgentS1(llm=s1_llm_client, api_context=api_context_string),
        "S2": AgentS2(llm=s2_llm_client, api_context=api_context_string),
    }

    # Collect run metadata
    run_mode = f"baseline_{args.agent}" if args.agent else "intelligent"
    run_metadata = {
        "timestamp": datetime.now().isoformat(),
        "dataset_path": args.dataset,
        "run_mode": run_mode,
        "confidence_threshold": args.confidence_threshold,
        "s1_model": args.s1_model,
        "s2_model": args.s2_model,
    }

    process_dataset(
        dataset_path=args.dataset,
        run_dir=args.run_dir,
        controller=controller,
        agents=agents,
        run_metadata=run_metadata,
    )


if __name__ == "__main__":
    main()
