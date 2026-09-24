# Upload the project to GitHub from Windows PowerShell

1. Open https://github.com/new while signed in. Repository name: `supportflow-rana-refaat`. Choose visibility suitable for your submission. **Leave the GitHub README, .gitignore, and license options unchecked** because those files already exist locally.
2. In PowerShell enter the **supportflow** folder containing `README.md` and run:

```powershell
git init
git add .
git status --short
git ls-files .env
```

The last command must print **nothing**. The `.gitignore` also excludes `runtime/` and `.venv/`. Look through the staged file list before continuing; do not upload personal tokens, secrets or databases.

```powershell
git commit -m "Add SupportFlow capstone"
git branch -M main
git remote add origin https://github.com/ranarefaat365-code/supportflow-rana-refaat.git
git push -u origin main
```

If your GitHub username is different, substitute it in the remote URL. If Git asks you to log in, complete its browser login. If Git asks for your author identity, set your own verified email address with `git config user.email "YOUR_GITHUB_EMAIL"` and name with `git config user.name "Rana Refaat"`, then repeat the commit and remaining commands. If `remote origin already exists`, use `git remote set-url origin https://github.com/ranarefaat365-code/supportflow-rana-refaat.git` before the push.

After pushing, refresh the repository page. Check that `README.md`, `architecture/SUPPORTFLOW_ARCHITECTURE.svg`, `frontend/dist/`, and `demo/NO_CODE_VIDEO_GUIDE.md` are visible, while `.env` and `runtime/` are absent. Use the resulting GitHub URL in your submission alongside your own demo video.
