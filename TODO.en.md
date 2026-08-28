[Deutsch](TODO.md) | [English](TODO.en.md) | [Overview](README.en.md) | [Changelog](CHANGELOG.md)

# TODO

Running list of open items. What's still open is at the top. Finished items
aren't deleted, they move down — with the date they were done.

## Open

### Next up

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

- **Store API access keys for the two Shopware shops.** One per sales channel.
- **Is by-hand enough?** If so, Meta's review is unnecessary altogether.
- **Public or private repository?** Private costs Actions minutes; the workflow
  is already in its frugal form.

## Done

- **Scaffolding** (2026-08-28): database, command line, the five projects, time
  handling, network directory, posting times, repeats. 109 tests.
- **Sources surveyed** (2026-08-28): which site has which interface is recorded
  in the [changelog](CHANGELOG.md).
