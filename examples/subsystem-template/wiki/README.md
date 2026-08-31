# Not a directory in your repo

These files belong in your repo's **GitHub wiki**, not in the repo itself. The wiki is
a separate git repo:

```sh
git clone https://github.com/<owner>/<repo>.wiki.git wiki
cp Home.md overview.md wiki/
cd wiki && git add -A && git commit -m "docs: seed the wiki" && git push
```

If the clone fails with "repository not found", the wiki doesn't exist yet — open the
repo's **Wiki** tab on github.com and save any first page, then clone again.

Do not commit this `README.md` to your wiki; it is scaffolding for the template only.
Full contract: <https://league-robotics.github.io/publishing/>
