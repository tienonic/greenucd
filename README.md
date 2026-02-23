# GREEN - UCD Website

Source code for the GREEN (Green Innovation Network) website at UC Davis — [carrotcore.com](https://carrotcore.com).

GREEN is a student-led AgTech organization at UC Davis focused on sustainable agriculture, renewable energy, and environmental technology.

All members are welcome to suggest edits by opening pull requests. Contact the webmaster at think@ucdavis.edu for help.

## Stack

Built with [Jekyll](https://jekyllrb.com/) (static site generator) and deployed to GitHub Pages via GitHub Actions.

## Content

- [`_pages`](/_pages) — site pages (URL structure mirrors folder structure)
- [`images`](/images) — images
- [`_data`](/_data) — structured data:
  - [`menu.yml`](_data/menu.yml) — navigation
  - [`officers.yml`](_data/officers.yml) — board members
  - [`positions.yml`](_data/positions.yml) — board positions

Pages are written in [Markdown](https://www.markdownguide.org/basic-syntax/) with YAML front matter.

## Deployment

Pushing to `main` automatically builds and deploys the site to [carrotcore.com](https://carrotcore.com) via GitHub Actions. Deployment takes a few minutes.

## Local Development

Requires Ruby, Bundler, and Jekyll. Or use Docker:

```
docker-compose up
```

Then open `localhost:4000`.
