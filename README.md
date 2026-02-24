# GREEN - UCD Website

This repository contains the source code of https://carrotcore.com.

GREEN (Green Innovation Network) is a student-led AgTech organization at UC Davis focused on sustainable agriculture, renewable energy, and environmental technology.

Built from a clone of the [MITOC website](https://github.com/mitoc/website).

All members of the GREEN community are welcome to suggest edits by opening pull requests!

If you'd like to change anything on the website, you can:
- Read the rest of this short document to figure out how things work
- Suggest a change on a file by clicking on the "Edit this file" button (see screenshot below). This will open a Pull Request (PR), which the webmasters will review. When the PR gets accepted and merged to the `main` version of the code, it will trigger an automatic deployment.
- Don't hesitate to contact GREEN webmaster at think@ucdavis.edu if you want any help!

## General

The website is built using [Jekyll](https://jekyllrb.com/), a static site generator.


## Content edition

### What to edit

The website content is located in the following directories:
- [`_pages`](/_pages) for pages
- [`images`](/images) for images and pictures
- [`_data`](/_data) for structured data used by the website. This includes:
  - [Menu items](_data/menu.yml)
  - Club [positions](_data/positions.yml) and [officers](_data/officers.yml)

The organization of the `_pages` folder follows the URL schema: the source of the `/activities/farming` page is `_pages/activities/farming.md`.

### Syntax

Page content is written in [Markdown](https://www.markdownguide.org/basic-syntax/).

On top of each page file, a "front matter" can also be found. It defines metadata about the page using the [YAML](https://lzone.de/cheat-sheet/YAML) format.

`_data` files are also written in YAML.

### Advanced - Use of HTML tags in Markdown

HTML tags can be included in Markdown files, but that should be used with moderation, and only for things that cannot be done just with Markdown.

For instance, to color a word:

```HTML
This <span style="color:red;">word</span> is red.
```

Or to apply a specific style to a block:

```HTML
<div class="well" markdown="1">

#### Can I reserve gear ahead of time?

No. All gear is first come, first served.

</div>
```

> Note the use of `markdown="1"`: this is necessary to render the Markdown located in the tag.

The styled class `well`, as well as many others, are brought by [Bootstrap 3.3.7](https://getbootstrap.com/docs/3.3/).

### Advanced - Templating

Tags starting by `{{` or `{%` are templating tags. They allow putting bits of HTML together, define reusable components, loop over data, etc.

If you're curious about that, please refer to the [Jekyll docs](https://jekyllrb.com/docs/liquid/).


## Live deployment

Pushing to `main` automatically deploys the site to https://carrotcore.com via GitHub Actions. Deployment should not take more than a few minutes.

## Local development

If you want to develop locally and see your changes before committing them to GitHub, you will need to use [Jekyll](https://jekyllrb.com/). This involves installing `Ruby`, `Bundler`, and `Jekyll`, then running a local web server. [GitHub has some instructions](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/testing-your-github-pages-site-locally-with-jekyll).

### Docker for Local Development

If you don't want to deal with Ruby version management, you can use `docker-compose`. Docker install [here](https://www.docker.com/get-started).

```
docker-compose up
```

Then navigate to `localhost:4000` to see a local copy of the site.
