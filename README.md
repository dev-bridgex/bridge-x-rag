# Bridge-X-RAG

This is a RAG application backend for Bridge-X (A Social / E-Learning Platform For Egyptian Universities 's Student Activity Teams)

## Requirements

- python 3.10 or later (required)
- uv 0.20 or later (recommended but not required)

### install python 3.10 using uv

1) download and install uv from [here](load uv from [here](https://docs.astral.sh/uv/getting-started/installation/)
2) install python 3.10 using uv

    ```bash
    uv install python 3.10
    ```

3) create a new virtual environment using uv

    ```bash
    uv vevn .venv
    ```

4) synchronize the project dependencies

    ```bash
    uv sync
    ```

5) run the project using uv (make sure you are in the project root(src) directory)

    ```bash
    uv run uvicorn api.main:app --reload --port 8000 --host 0.0.0.0
    ```

### (Optional) Setup you command line interface for better readability

```bash
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "
```
