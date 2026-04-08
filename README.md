\# LiveCodeBench integration



Скрипт `run\_promptpulse.py` позволяет протестировать одну и ту же базовую модель

(например, `openai:gpt-5.4`) и ту же модель под управлением двух AI Super Agents

из API на бенчмарке LiveCodeBench (сценарий codegeneration).



В начале `run\_promptpulse.py` задайте:



```python

BASE\_URL = "https://llm-manager.etacar.io/api/external"

API\_TOKEN = "ВАШ\_API\_КЛЮЧ"

MODEL\_ID = "openai:gpt-5.4"
```



\## Запуск бенчмарка



\### 1. Установка LiveCodeBench



```bash

git clone https://github.com/LiveCodeBench/LiveCodeBench.git

cd LiveCodeBench



\# venv + зависимости

python -m venv .venv

source .venv/bin/activate



uv pip install "datasets==2.20.0"

uv pip install -e .

uv pip install requests tqdm

```



Положите `run\_promptpulse.py` в корень репозитория.



\### 2. Генерация ответов модели



Скрипт поддерживает три режима:



\- `base` — базовая модель без агента

\- `agent1` — модель под первым доступным супер-агентом (`aiSuperAgents\[0]`)

\- `agent2` — модель под вторым супер-агентом (`aiSuperAgents\[1]`)



Примеры:



```bash

\# Базовая модель

python run\_promptpulse.py --mode base --n\_samples 846



\# Модель под первым агентом

python run\_promptpulse.py --mode agent1 --n\_samples 846



\# Модель под вторым агентом

python run\_promptpulse.py --mode agent2 --n\_samples 846

```



Флаг `--n\_samples` задает количество задач (по умолчанию 10; `None` = все задачи).



Результаты сохраняются в:



\- `output/promptpulse\_base\_outputs.json`

\- `output/promptpulse\_agent1\_outputs.json`

\- `output/promptpulse\_agent2\_outputs.json`



Формат:



```json

\[

&#x20; {

&#x20;   "question\_id": "xxx",

&#x20;   "code\_list": \["... сгенерированный код ..."]

&#x20; },

&#x20; ...

]

```



\### 3. Оценка результатов через LiveCodeBench



Для каждого из трех файлов выполните:



```bash

python -m lcb\_runner.runner.custom\_evaluator \\

&#x20; --custom\_output\_file output/promptpulse\_base\_outputs.json \\

&#x20; --scenario codegeneration



python -m lcb\_runner.runner.custom\_evaluator \\

&#x20; --custom\_output\_file output/promptpulse\_agent1\_outputs.json \\

&#x20; --scenario codegeneration



python -m lcb\_runner.runner.custom\_evaluator \\

&#x20; --custom\_output\_file output/promptpulse\_agent2\_outputs.json \\

&#x20; --scenario codegeneration

```



`custom\_evaluator`:



\- загружает тот же датасет LiveCodeBench (`code\_generation\_lite`, release\_v5),

\- выравнивает результаты по `question\_id`,

\- компилирует и запускает код на тестах,

\- считает метрики по бенчу и сохраняет их в `\*\_eval.json`.

