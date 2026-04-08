import requests
import json
import time
import argparse
from datasets import load_dataset
from tqdm import tqdm

# КОНФИГУРАЦИЯ

BASE_URL = "https://llm-manager.etacar.io/api/external"
API_TOKEN = ""
MODEL_ID = "openai:gpt-5.4" 

HEADERS = {
    "x-api-token": API_TOKEN,
    "Content-Type": "application/json",
}

RELEASE_VERSION = "release_v5"
N_SAMPLES = 10                  


def get_available_models() -> list:
    resp = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["models"]


def get_super_agents() -> list:
    resp = requests.get(f"{BASE_URL}/ai-super-agents", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["aiSuperAgents"]


def create_conversation(title: str, model_id: str, agent_id: str = None) -> str:
    payload = {"title": title, "model": model_id}
    if agent_id:
        payload["aiSuperAgent"] = agent_id
    resp = requests.post(f"{BASE_URL}/conversations", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["_id"]


def send_message(conv_id: str, message: str, agent_id: str = None) -> str:
    payload = {"message": message}
    if agent_id:
        payload["aiSuperAgent"] = agent_id
    url = f"{BASE_URL}/conversations/{conv_id}/messages"
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()["assistantMessage"]["content"]


def delete_conversation(conv_id: str):
    try:
        requests.delete(f"{BASE_URL}/conversations/{conv_id}", headers=HEADERS, timeout=30)
    except Exception:
        pass


def format_prompt(problem: dict) -> str:
    title = problem.get("question_title", "")
    content = problem.get("question_content", "")
    starter = problem.get("starter_code", "")
    
    prompt = f"### Coding Problem\n\n{title}\n\n{content}"
    if starter:
        prompt += f"\n\n### Starter Code\n```python\n{starter}\n```"
    prompt += "\n\n### Your Solution\nWrite a complete Python solution. Output only the code, no explanations."
    return prompt


def run_benchmark(mode: str, agent_id: str = None, n_samples: int = None) -> list:
    print(f"Режим: {mode}")
    print(f"Агент: {agent_id or 'нет (базовая модель)'}")
    print(f"Загрузка датасета {RELEASE_VERSION}...")

    dataset = load_dataset(
        "livecodebench/code_generation_lite",
        split="test",
        trust_remote_code=True,
        version_tag="release_v5"
    )

    if n_samples:
        dataset = dataset.select(range(min(n_samples, len(dataset))))

    print(f"Задач для прогона: {len(dataset)}")

    results = []

    for i, problem in enumerate(tqdm(dataset, desc=f"[{mode}] Прогон задач")):
        question_id = problem["question_id"]
        prompt = format_prompt(problem)

        conv_id = None
        try:
            conv_id = create_conversation(
                title=f"LCB task {question_id}",
                model_id=MODEL_ID,
                agent_id=agent_id,
            )

            answer = send_message(conv_id, prompt, agent_id=agent_id)

            results.append({
                "question_id": question_id,
                "code_list": [answer],
            })

        except Exception as e:
            print(f"\n[!] Ошибка на задаче {question_id}: {e}")
            results.append({
                "question_id": question_id,
                "code_list": [""],
            })

        finally:
            if conv_id:
                delete_conversation(conv_id)

        time.sleep(0.5)

    return results


def main():
    parser = argparse.ArgumentParser(description="LiveCodeBench runner")
    parser.add_argument(
        "--mode",
        choices=["base", "agent1", "agent2"],
        required=True,
        help="Режим: base (базовая модель), agent1, agent2 (под супер-агентом)",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=N_SAMPLES,
        help="Кол-во задач (по умолчанию 10, None = все)",
    )
    args = parser.parse_args()


    print("Получаем список супер-агентов...")
    agents = get_super_agents()
    for idx, ag in enumerate(agents):
        print(f"  [{idx}] id={ag['_id']}  name={ag.get('name', '?')}")


    agent_id = None
    if args.mode == "agent1" and len(agents) > 0:
        agent_id = agents[0]["_id"]
        print(f"Используем агента: {agents[0].get('name')} ({agent_id})")
    elif args.mode == "agent2" and len(agents) > 1:
        agent_id = agents[1]["_id"]
        print(f"Используем агента: {agents[1].get('name')} ({agent_id})")
    elif args.mode != "base":
        print(f"[!] Режим {args.mode}: агент не найден, запускаем без агента.")


    results = run_benchmark(
        mode=args.mode,
        agent_id=agent_id,
        n_samples=args.n_samples,
    )

    out_file = f"output/promptpulse_{args.mode}_outputs.json"
    import os
    os.makedirs("output", exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Сохранено {len(results)} результатов → {out_file}")
    print(f"\nСледующий шаг — запустить оценку:")
    print(f"  python -m lcb_runner.runner.custom_evaluator \\")
    print(f"    --custom_output_file {out_file} \\")
    print(f"    --scenario codegeneration")


if __name__ == "__main__":
    main()