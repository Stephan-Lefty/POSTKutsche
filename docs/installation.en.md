[Deutsch](installation.md) | [English](installation.en.md) | [Overview](../README.en.md) | [Using it](bedienung.en.md) | [Changelog](../CHANGELOG.md)

# Installation

From a bare machine to a running calendar. How to work with it afterwards is
in the [user guide](bedienung.en.md).

This assumes Linux and a machine of your own – a workstation or a small
server. Multi-user operation is not intended: POSTKutsche has no login and
listens on `localhost` only.

## Contents

- [What you need](#what-you-need)
- [1. Install the program](#1-install-the-program)
- [2. Create the store](#2-create-the-store)
- [3. Enter your own sites](#3-enter-your-own-sites)
- [4. Connect Claude](#4-connect-claude)
- [5. Set up accounts](#5-set-up-accounts)
- [6. Set up continuous operation](#6-set-up-continuous-operation)
- [Where things are put](#where-things-are-put)
- [Checking that it all stands](#checking-that-it-all-stands)
- [Removing it again](#removing-it-again)

## What you need

**Python 3.11 or newer.** Nothing else – the core comes without third-party
packages. Database, web service and every fetch sit in the standard library.
That is deliberate: a tool you set up once and then run for years should not
depend on a library that may be gone in two.

Two things are optional and can be added later:

| Package | What for | Without it |
|---|---|---|
| Pillow | crop images to 4:5 | the unmodified image from the website is used – it looks worse on a phone |
| keyring | access tokens in the keyring | tokens go into `~/.config/postkutsche/zugaenge.json` with mode 600 |

Writing the texts needs **Claude Code** (step 4), continuous operation needs
**systemd** (step 6). Neither is required just to have a first look.

## 1. Install the program

```
git clone https://github.com/Stephan-Lefty/POSTKutsche.git
cd POSTKutsche
python -m venv .venv
source .venv/bin/activate
pip install -e ".[alles]"
```

`-e` means editable: the program runs from the folder it sits in. For the
optional parts individually use `".[bilder]"` or `".[schluessel]"`; for
neither, plain `pip install -e .`.

After that the `postkutsche` command exists:

```
postkutsche --fassung
```

## 2. Create the store

```
postkutsche einrichten
```

This creates the database at `~/.local/share/postkutsche/postkutsche.db` and
enters five example projects – a blog, a shop, a site without an API and so
on, all with `.example` addresses. That is enough to look at the interface
without anything being fetched anywhere.

A look at the calendar, without anything having to run permanently yet:

```
postkutsche kalender
```

The browser opens `http://localhost:8770`. With `--nicht-oeffnen` it stays
closed, with `--port` the service runs elsewhere.

## 3. Enter your own sites

**Your own addresses do not go into the repository.** They go into
`~/.config/postkutsche/projekte.json`, and nowhere else. A public repository
is searchable, gets cloned and ends up in search engines; whoever reads it
learns which shops someone runs and which manufacturers they work with – a
picture that shouldn't be anywhere. And what once stood in the version
history is still in there after being deleted.

```json
[
  {
    "kennung": "meinblog",
    "name": "Mein Blog",
    "adresse": "https://meinblog.example",
    "art": "wordpress",
    "farbe": "#6bad08",
    "einstellungen": {
      "rest": "https://meinblog.example/wp-json/wp/v2",
      "zielgruppe": "verbraucher"
    }
  }
]
```

There are three kinds:

- **`wordpress`** – the REST API under `/wp-json/wp/v2/`. It is open on most
  blogs and delivers title, text, featured image, categories and the
  publication date.
- **`seitenkarte`** – for sites without any API: read `sitemap.xml`, scrape
  the page itself, take the image from `og:image`. Shopware shops work this
  way too; no access key needed.
- **`shopware`** – the Store API. Provided for, but not built out; use
  `seitenkarte`.

`zielgruppe` steers the suggested posting times and is one of `handwerk`,
`verbraucher`, `betroffene` or `gemischt`. A bilingual blog needs a language
filter, otherwise the other language is counted and planned along:

```json
"einstellungen": { "ausschliessen": ["/en/"] }
```

For campaigns by manufacturer there is a `hersteller.json` next to it; what
it looks like is in the [README](../README.en.md#adding-your-own-sites).

A project can also be created without the file, straight from the command
line:

```
postkutsche projekt neu meinblog "Mein Blog" https://meinblog.example --art wordpress
postkutsche projekt liste
```

## 4. Connect Claude

The texts are written by Claude, called through the command line – that uses
an existing subscription, costs nothing per post and needs no key to manage.

```
npm install -g @anthropic-ai/claude-code
claude
```

On first start enter `/login` once and sign in. After that POSTKutsche finds
the command by itself. If it is missing, the program says exactly that and
names these two lines – it does not guess and does not write half a text.

The proof, once a project is entered:

```
postkutsche entwerfen --projekt meinblog --anzahl 1
```

## 5. Set up accounts

Creating an account, here Mastodon:

```
postkutsche konto neu mastodon mastodon-privat --instanz https://mastodon.example
postkutsche konto token mastodon-privat
postkutsche konto pruefen mastodon-privat
```

You create the token on your own Mastodon server, as a new application in
your account settings. Two scopes are enough: `write:statuses`, plus
`write:media` for images. Don't grant more – a token that may only write
cannot give anything away.

While typing, the token stays invisible and goes into the keyring; if there
is none, into `~/.config/postkutsche/zugaenge.json` with mode 600. **It never
goes into the database.** A test makes sure the accounts table never gets a
column containing »token«, »passwort« or »secret«.

`konto pruefen` asks the network without sending anything.

Facebook and Instagram need no account: they run by hand, see
[using it](bedienung.en.md#publishing).

## 6. Set up continuous operation

```
postkutsche dienst einrichten
```

This puts three units into `~/.config/systemd/user/` and starts them:

| Unit | What for |
|---|---|
| `postkutsche-kalender.service` | keeps the interface running on `localhost:8770` |
| `postkutsche-senden.service` | sends what is due |
| `postkutsche-senden.timer` | triggers that every five minutes |

The timer is `Persistent=true`: if the machine was off at posting time, the
post goes out on the next start rather than not at all.

For this to run without a logged-in session – on a server, or when you log
out – one more step is needed:

```
sudo loginctl enable-linger $USER
```

An entry in the application menu, if wanted:

```
postkutsche dienst menueeintrag
```

## Where things are put

| What | Where |
|---|---|
| database | `~/.local/share/postkutsche/postkutsche.db` |
| own projects | `~/.config/postkutsche/projekte.json` |
| own manufacturers | `~/.config/postkutsche/hersteller.json` |
| tokens without a keyring | `~/.config/postkutsche/zugaenge.json` (600) |
| cache, images | `~/.local/share/postkutsche/` |
| filed images | `~/Dokumente/POSTKutsche/<year>-KW<week>/<project>/` |
| systemd units | `~/.config/systemd/user/` |

Two environment variables move that where needed: `POSTKUTSCHE_CONFIG` for
the configuration folder, `POSTKUTSCHE_DOKUMENTE` for the image location.
What the documents folder is called is otherwise asked of the system rather
than guessed – on an English system it is »Documents«.

The database can be redirected with `--ablage`, for trying things out:

```
postkutsche --ablage /tmp/probe.db einrichten
```

## Checking that it all stands

```
postkutsche dienst stand           # are calendar and timer running?
postkutsche projekt liste          # are the projects there?
postkutsche konto liste            # are the accounts there?
postkutsche senden --probelauf     # what would go out now?
python -m unittest discover -s tests
```

`--probelauf` sends nothing, it only shows what would be due. The tests run
without network access: sources are checked against recorded responses, the
Claude connection against a faked call.

## Removing it again

```
postkutsche dienst entfernen
pip uninstall postkutsche
```

`dienst entfernen` stops the units and deletes them. What you produced stays:
database, configuration and filed images remain in the folders above and have
to be removed by hand if they should go.
