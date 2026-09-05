[Deutsch](TODO.md) | [English](TODO.en.md) | [Overview](README.en.md) | [Changelog](CHANGELOG.md)

# TODO

Running list of open items. What's still open is at the top. Finished items
aren't deleted, they move down — with the date they were done.

## Open

### Next up

- **DialOS has enough posts for one week.** Eight German posts are available,
  a week wants seven days. Plan them once and there is almost nothing left for
  four weeks – the cooling-off period blocks whatever has already run. Either
  fewer days per week, or a shorter period than 28 days for blogs. Decide in
  operation, not before.
- **Spreading doesn't know about recency on blogs.** Selection goes by name
  stem and alphabet – right for product variants, arbitrary for blog posts. A
  post published yesterday therefore isn't necessarily at the front. For
  picking up older texts again that hardly matters; building a week around a
  fresh post is where it shows. The automatic route via "holen" doesn't have
  this problem.
- **A top-up from the sitemap for thin categories?** Of the addresses only the
  sitemap knows and the navigation does not link, a measured eleven per cent
  are still alive – too few to draw on in general. One category was the
  exception: there all five are alive. If that turns out to be common, a
  top-up for undersized categories would be worth considering – but only once
  it shows up while planning.
- **Odds and ends in the category list that nobody has named yet.**
  Configurators and pickup regions are out. Going through the 116 also turned
  up "offers" and "offers and pickup stock" (catch-alls rather than ranges)
  and two categories whose label is broken in the page's encoding. None of it
  removed on suspicion – one word is enough if it bothers you.
- **Sharpen the collected knowledge once it settles in.** Open questions:
  whether twelve entries per instruction are enough, and whether the newest
  ones are the right ones. Taking an answer back currently means deleting it
  and answering again – there is no editing.
- **A third image.** Two fit in two columns; a third calls for a table of its
  own, with an order column. Doing it earlier would mean guessing how many
  there will be.
- **The second image through the API as well.** Mastodon would take four,
  our sender attaches one. Until then the second image belongs to the
  by-hand mode – the interface says so, but it isn't pretty.
- **Connect the sources.** WordPress via `/wp-json/wp/v2/posts?_embed`,
  Shopware 6 via the Store API, altbau.example via `sitemap.xml` and `og:` scraping.
  One test per source against a recorded response, no network in tests.
- **Connect Claude.** `claude -p` with a fixed output format, instructions per
  network. Tested against a faked call.
- **Web interface.** Calendar in month and week view, project column on the
  left for showing and hiding, cards in project colour with a network stripe,
  drag to move the date.
- **Mastodon.** The first network to run end to end — from blog post to
  published post. Usable immediately, no review process.
- **By-hand mode for Facebook and Instagram.** A handover view with text to
  copy (plain, no markdown characters), image cropped to 4:5 to download, and a
  "published by hand" button.

### After that

- **LinkedIn.** Own profile, `w_member_social`. The token expires after 60 days;
  renewal has to happen on its own and must not fail on the weekend it falls due.
- **Images.** Crop to 4:5 (1080×1350) with Pillow. Without Pillow, use the
  original image from the website.
- **Somewhere to put Instagram images.** Instagram doesn't accept a file — Meta
  fetches the image from a public address itself. Cropped images therefore need
  a place on the web (SFTP to your own webspace), or the unmodified image from
  your own site is used.
- **Schedule.** A systemd user timer that sends what's due every five minutes.
  If the machine was off, the post must go out on next start — with a note about
  the delay, not silently.
- **Measure response.** The times in `sendezeiten.py` are estimates from
  industry studies. Once enough of our own posts are out: collect reactions and
  replace the estimates with our own numbers.
- **Warn about duplicates.** When repeating a post, you should see how similar
  the new text is to the old one. Facebook and Instagram throttle verbatim
  repeats.
- **Facebook and Instagram via the API.** Only if operation shows that the
  by-hand mode isn't enough. Meta's app review takes two to four weeks per
  submission.

### Questions to settle in operation

- **Is by-hand enough?** If so, Meta's review is unnecessary altogether.
- **Public or private repository?** Private costs Actions minutes; the workflow
  is already in its frugal form.

## Done

- **Scaffolding** (2026-08-28): database, command line, the five projects, time
  handling, network directory, posting times, repeats. 109 tests.
- **Sources surveyed** (2026-08-28): which site has which interface is recorded
  in the [changelog](CHANGELOG.md).
- **The two Shopware shops connected** (2026-08-31): through the sitemap, no
  access key needed. They now carry the kind »seitenkarte« and can be picked
  in "plan a week"; their categories are listed in the project file, because
  with Shopware the sitemap doesn't reveal what a category contains.
- **Dead categories sorted out** (2026-08-31): the planning window offered
  categories that no longer exist.
- **The range now comes from the navigation** (2026-08-31): at first it was
  only a filter over the sitemap, and what got offered was the intersection –
  17 categories where the shop carries 116. The navigation is the source now,
  read down to the third level, with product counts tallied while reading and
  kept for twelve hours.
- **Answers to queries become project knowledge** (2026-08-31): when you
  answer, a switch says whether the answer holds in general or only for this
  product. General knowledge goes into every further draft, product knowledge
  only for its own address. Reviewed and deleted under "Gelerntes".
- **Images get a place, and a post gets two** (2026-08-31): the service files
  them under `~/Dokumente/POSTKutsche/<year>-KW<week>/<project>/`, because the
  browser decides where a download lands and a web page cannot change that. A
  version now carries two images, both cropped to 4:5.
- **Categories spanning more than one page** (2026-08-31): three of 119 have a
  second page, twelve products in total – all three had been sitting at
  exactly 30. Only pages the category links itself are followed; guessing
  "?page=2" goes wrong because a page that doesn't exist rarely answers 404.
- **Cancelling actually cancels** (2026-08-31): the button used to close the
  window only – the run carried on inside the service, kept creating posts and
  held the lock. Measured: stopping mid-run left five posts in the database
  and five of ten products counted as promoted. The run now stops between two
  products and takes back what it created.
- **Blogs in the weekly planning** (2026-09-05): the two WordPress projects
  can be planned like a shop. The categories come from WordPress itself, the
  text through the API instead of out of the HTML, and Claude gets its own
  rules for blog posts – including the publication date, so a post from March
  isn't announced as new. Overlong posts are trimmed at paragraph boundaries.
