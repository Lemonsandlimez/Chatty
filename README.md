# Chatty - A Tiny, Fast, Dependency-Free Memory Engine

Chatty is a lightweight engine that can create AI-like performance with little to no RAM usage.
It lets your apps store, recall, and search info instantly using only Python and SQLite.

## 🚀 Features

1. Zero Dependancies
2. Fast Training (10,000 items in 0.5 seconds)
3. Insanely Tiny Footprint
4. Category-Aware Memory
5. Portable (works anywhere Python does)
6. Simple (no weird logic adapters)

## 🤖 Chatty vs Chatterbot

Chatty and Chatterbot may seem exactly the same, but they are **heavily** different.

**Chatterbot requires SQLAlchemy, mathparse, nltk, spacy, and more**
**Chatty does.. not**

**Chatterbot is slow (10-30 minutes for 10,000 items!)**
**Chatty is a ton faster (10,000 items in *half* a second)**

**Chatterbot tries to be AI-ish**
**Chatty embraces being a Memory Engine, not a fake AI**

## 🧑‍💻 Using It

Add a fact:

```python
mem.AddFact("2 + 2 is 4", Category="Math")
```

Or for a permanant fact:

```python
mem.AddFactPerm("The sun is a star.")
```

Search for a fact:

```python
result = mem.SearchFacts("does apple make the iPhone", TopK=1)
print(result[0]["Text"])
```

Categorys make Chatty a ton smarter:

```python
mem.AddFact("Python is a programming language.", Category="Tech")
mem.AddFact("Python is a type of snake.", Category="Animals")
```

## 🔧 Where to Use Chatty

Here is a tiny but real list:

1. Discord Bots
2. NPCs or Games
3. Websites or Shop AI Helpers
4. Low RAM Systems (Rasberry Pi 0 can easily run it, while not as fast, it can)
5. CLI Tools

**If it runs Python, it runs Chatty**

## 🤔 Why Chatty

Because sometimes you don't need a 4GB Transformer Model.

You need something **tiny** **fast** and **local** that works anywhere.

Chatty is:

* Simple
* Predictable
* Portable
* Dependency-Free
* And fun to use

It fits in places where other libaries can't.
