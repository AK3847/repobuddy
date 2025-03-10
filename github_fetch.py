import os
import subprocess
import logging
from urllib.parse import urlparse

def download_git_repo(repo_url, target_directory=None):

    try:
        parsed_url = urlparse(repo_url)
        repo_path = parsed_url.path
        repo_name = os.path.basename(repo_path)
        user_name = os.path.dirname(repo_path).strip('/')
        
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        
        if target_directory is None:
            target_directory = os.getcwd()
        else:
            os.makedirs(target_directory, exist_ok=True)
        
        repo_dir = os.path.join(target_directory, user_name+"/"+repo_name)
        
        if os.path.exists(repo_dir):
            logging.warning(f"Directory {repo_dir} already exists. Skipping clone.")
            return repo_dir
            
        logging.info(f"Cloning repository {repo_url} to {repo_dir}")
        subprocess.run(
            ["git", "clone", repo_url, repo_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logging.info(f"Repository successfully cloned to {repo_dir}")
        return repo_dir
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to clone repository: {e}")
    except Exception as e:
        raise Exception(f"Failed to download repository: {str(e)}")