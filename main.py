import logging
from pathlib import Path
from typing import Dict
from ollama import Client
import time
from github_fetch import download_git_repo
import tiktoken

encoding = tiktoken.encoding_for_model("gpt-4o-mini")

current_time = time.strftime("%M,%H,%d,%m,%Y", time.localtime()).replace(",", "_")

## Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_repo_files(repo_path: str) -> Dict[str, str]:
    files_dict = {}
    repo_path = Path(repo_path)

    logging.info(f"Collecting Flutter project files from repository at {repo_path}")

    try:
        readme_candidates = ["README.md", "README", "Readme.md", "readme.md"]
        for readme_name in readme_candidates:
            readme_path = repo_path / readme_name
            if readme_path.exists() and readme_path.is_file():
                try:
                    with open(
                        readme_path, "r", encoding="utf-8", errors="replace"
                    ) as f:
                        content = f.read()
                    files_dict[str(readme_path.relative_to(repo_path))] = content
                    logging.info(f"Added README file: {readme_path}")
                    break
                except Exception as e:
                    logging.warning(
                        f"Couldn't read README file {readme_path}: {str(e)}"
                    )

        # check for pubspec.yaml file
        pubspec_path = repo_path / "pubspec.yaml"
        if pubspec_path.exists() and pubspec_path.is_file():
            try:
                with open(pubspec_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                files_dict["pubspec.yaml"] = content
                logging.info("Added pubspec.yaml file")
            except Exception as e:
                logging.warning(f"Couldn't read pubspec.yaml file: {str(e)}")

        lib_dir = repo_path / "lib"
        if lib_dir.exists() and lib_dir.is_dir():
            for file_path in lib_dir.rglob("*"):
                if file_path.is_dir():
                    continue

                if file_path.suffix.lower() != ".dart":
                    continue

                ## File size limit --> 2MB
                if file_path.stat().st_size > 2_000_000:
                    logging.warning(f"Skipping large file: {file_path}")
                    continue

                try:
                    relative_path = str(file_path.relative_to(repo_path))
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    files_dict[relative_path] = content
                except Exception as e:
                    logging.warning(f"Couldn't read file {file_path}: {str(e)}")
        else:
            logging.warning("No lib directory found in the Flutter project")

        logging.info(f"Collected {len(files_dict)} files from Flutter project")
        return files_dict
    except Exception as e:
        logging.error(f"Error collecting Flutter project files: {str(e)}")
        raise


def analyze_repo_with_llm(repo_path: str, user_prompt: str):
    logging.info(f"Starting repository analysis with prompt: {user_prompt}")

    files = get_repo_files(repo_path)

    system_prompt = open("system_prompt.txt").read()
    file_content = ""

    for file_path, content in files.items():
        content_sample = (
            content[:25000] + "... [truncated]"
            if len(content) > 1000
            else content  ## File length limit --> 25,000 characters
        )
        file_content += f"## File: {file_path}\n```\n{content_sample}\n```\n\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": file_content},
    ]

    logging.info(f"Total tokens: {len(encoding.encode(file_content))}")
    logging.info("Sending repository contents to LLM for analysis")

    try:
        full_response = ""
        print("\nAnalyzing repository...\n")
        client = Client()
        response = client.chat(
            model="llama3.2:1b-instruct-fp16",  ## trial model
            messages=messages,
            stream=True,
            options={
                "num_ctx": 4096  ## context length
            },
        )
        for part in response:
            print(part["message"]["content"], end="", flush=True)
        print("\n\nAnalysis complete.")

        with open(f"analysis_result_{current_time}.md", "w+") as f:
            f.write(f"## Analysis report of {repo_path} \n")
            f.write(full_response)

    except Exception as e:
        logging.error(f"Error during LLM analysis: {str(e)}")
        print(f"\nError during analysis: {str(e)}")


if __name__ == "__main__":
    user_query = input("Give your github url: ")
    try:
        repo_path = download_git_repo(user_query)
        logging.info(f"Repository downloaded successfully to: {repo_path}")

        # user_prompt = input("\nWhat would you like to know about this repository: ")
        user_prompt = (
            # "Only list out all the files (with their proper path) present in the repo given to you, do not suggest any other extra files"
            "List out all the dependencies of the given flutter project from the pubspec.yaml file"
        )
        analyze_repo_with_llm(repo_path, user_prompt)

    except Exception as e:
        print(f"Error: {str(e)}")
