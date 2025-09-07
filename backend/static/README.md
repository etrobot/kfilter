This directory serves the built frontend assets at runtime.

Recommended workflow:
- In development: run the frontend separately via Vite.
- For production Docker builds: the Dockerfile builds the frontend and copies the output to this directory.

Git policy:
- A local .gitignore ignores all generated files here.
- Keep this README.md and .gitignore under version control.
- If the repository already tracks files in this directory (e.g. previous commits), remove them from Git cache:

Commands to clean tracked files (run at repo root):

  git rm -r --cached backend/static
  git add backend/static/.gitignore backend/static/README.md
  git commit -m "chore: ignore built static assets and keep dir"
