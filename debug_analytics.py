import asyncio
import sys
sys.path.insert(0, "/Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game")

async def main():
    from src.visualization.analytics import get_analytics_engine
    
    engine = get_analytics_engine()
    print(f"All players: {engine.all_players}")
    print(f"Opponent models keys: {list(engine.opponent_models.keys())}")
    print(f"Counterfactuals keys: {list(engine.counterfactuals.keys())}")
    
    for player_id in engine.all_players:
        models = engine.get_all_opponent_models(player_id)
        print(f"Player {player_id} has {len(models)} opponent models")
        
asyncio.run(main())
