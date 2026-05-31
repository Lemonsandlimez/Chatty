import sqlite3
import json
import time
import math
import re
import os
import asyncio
from collections import Counter

# text cleanup

def NormalizeRepeats(word: str, max_repeats=2, preserve_vowels=True):
    # shorten long words
    if preserve_vowels:
        pattern = r'([bcdfghjklmnpqrstvwxyz])\1{' + str(max_repeats) + r',}'
    else:
        pattern = r'(.)\1{' + str(max_repeats) + r',}'

    replacement = r'\1' * max_repeats
    return re.sub(pattern, replacement, word)


def SoftFix(word: str) -> str:
    # Apply repeat shortening
    return NormalizeRepeats(word, max_repeats=2, preserve_vowels=True)


def Normalize(text: str) -> str:
    # Lowercase and normalize each word
    text = text.lower()
    words = text.split()
    return " ".join(SoftFix(w) for w in words)


# embed

def EmbedText(Text: str) -> dict[str, int]:
    # Turn text into a word-frequency map.

    Text = Normalize(Text)
    CleanText = re.sub(r'[^\w\s]', '', Text)
    Words = CleanText.split()

    StopWords = {"the","is","a","an","and","or","in","on","to","for","of","it"}

    counts = Counter(Words)
    return {w: c for w, c in counts.items() if w not in StopWords}


# vector math

def CosineSimilarity(A: dict[str, int], B: dict[str, int]) -> float:
    Dot = sum(A.get(K, 0) * B.get(K, 0) for K in A)
    Na = math.sqrt(sum(V * V for V in A.values()))
    Nb = math.sqrt(sum(V * V for V in B.values()))
    return Dot / (Na * Nb + 1e-9)


def DecayWeight(W, T, HalfLife=86400):
    Age = time.time() - T
    return W * (0.5 ** (Age / HalfLife))


# the memory system 
class Memory:
    def __init__(self, MemoryFile="ChattyMemory.db"):
        self.MemoryFile = MemoryFile
        self.DB = sqlite3.connect(MemoryFile, check_same_thread=False)
        self.DB.row_factory = sqlite3.Row

        # speed settings
        self.DB.execute("PRAGMA journal_mode=WAL;")
        self.DB.execute("PRAGMA synchronous=OFF;")
        self.DB.execute("PRAGMA temp_store=MEMORY;")
        self.DB.execute("PRAGMA cache_size=-200000;")
        try:
            self.DB.execute("PRAGMA mmap_size=30000000000;")
        except:
            pass

        self.ShortTerm = {}
        self.NonDecayCategories = {"Permanent"}

        self._InitTables()
        self._LoadPermanentCategories()

    def _InitTables(self):
        Cur = self.DB.cursor()

        Cur.execute("""
            CREATE TABLE IF NOT EXISTS Keys (
                Key TEXT PRIMARY KEY,
                Value TEXT
            )
        """)

        Cur.execute("""
            CREATE TABLE IF NOT EXISTS Facts (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Text TEXT,
                Embedding TEXT,
                Weight REAL,
                Timestamp REAL,
                Category TEXT
            )
        """)

        self.DB.commit()

    def _LoadPermanentCategories(self):
        for row in self.DB.execute("SELECT Key FROM Keys WHERE Key LIKE 'NonDecay_%'"):
            cat = row["Key"].replace("NonDecay_", "")
            self.NonDecayCategories.add(cat)

    # perm 

    def MakePermanent(self, category: str):
        self.NonDecayCategories.add(category)
        self.RememberLong(f"NonDecay_{category}", "1")

    # training

    def Train(self, array, Category="General"):
        Cur = self.DB.cursor()
        Cur.execute("BEGIN IMMEDIATE TRANSACTION")

        now = time.time()
        insert_sql = """
            INSERT INTO Facts(Text, Embedding, Weight, Timestamp, Category)
            VALUES (?, ?, ?, ?, ?)
        """

        for fact in array:
            Emb = json.dumps(EmbedText(fact))
            Cur.execute(insert_sql, (fact, Emb, 1.0, now, Category))

        self.DB.commit()

    async def train_async(self, array, Category="General"):
        await asyncio.to_thread(self.train, array, Category)

    def trainperm(self, array, Category="Permanent"):
        print(f"Chatty is memorizing {len(array)} items forever...")
        Cur = self.DB.cursor()
        Cur.execute("BEGIN IMMEDIATE TRANSACTION")

        now = time.time()
        insert_sql = """
            INSERT INTO Facts(Text, Embedding, Weight, Timestamp, Category)
            VALUES (?, ?, ?, ?, ?)
        """

        for fact in array:
            Emb = json.dumps(EmbedText(fact))
            Cur.execute(insert_sql, (fact, Emb, 1.0, now, Category))

        self.DB.commit()
        print("Permanent training complete.")

    async def trainperm_async(self, array, Category="Permanent"):
        await asyncio.to_thread(self.trainperm, array, Category)

    # self-learning (this is only here for my old scripts. and because y not? )

    def ForeverLearn(self, response: str, learn_facts: list[str],
                     LearnRate=0.2, DecayRate=0.1):

        ResponseVec = EmbedText(response)
        Cur = self.DB.cursor()
        Cur.execute("SELECT * FROM Facts")
        Rows = Cur.fetchall()

        Updated = 0

        for R in Rows:
            FactText = R["Text"]
            FactVec = json.loads(R["Embedding"])
            Similarity = CosineSimilarity(ResponseVec, FactVec)
            ShouldStrengthen = FactText in learn_facts
            OldWeight = R["Weight"]

            if ShouldStrengthen:
                if Similarity > 0.5:
                    NewWeight = OldWeight + LearnRate
                else:
                    NewWeight = OldWeight - DecayRate
            else:
                NewWeight = OldWeight - (DecayRate * 0.5)

            NewWeight = max(0.1, min(NewWeight, 5.0))

            Cur.execute("UPDATE Facts SET Weight=? WHERE ID=?", (NewWeight, R["ID"]))
            Updated += 1

        self.DB.commit()
        return Updated

    # search

    def SearchFacts(self, Query, TopK=3):
        QVec = EmbedText(Query)
        Cur = self.DB.cursor()
        Cur.execute("SELECT * FROM Facts")
        Rows = Cur.fetchall()

        Scored = []

        for R in Rows:
            Emb = json.loads(R["Embedding"])
            Sim = CosineSimilarity(QVec, Emb)

            if R["Category"] in self.NonDecayCategories:
                Score = Sim * R["Weight"]
            else:
                Score = DecayWeight(Sim * R["Weight"], R["Timestamp"])

            Scored.append((Score, R))

        Scored.sort(key=lambda X: X[0], reverse=True)

        Results = []
        for Score, R in Scored[:TopK]:
            if Score > 0.05:
                Results.append({
                    "Text": R["Text"],
                    "Score": Score,
                    "Category": R["Category"]
                })

        return Results

    async def SearchFacts_async(self, Query, TopK=3):
        return await asyncio.to_thread(self.SearchFacts, Query, TopK)

    # short term smemory

    def RememberShort(self, Key, Value):
        self.ShortTerm[Key] = Value

    def RecallShort(self, Key, Default=None):
        return self.ShortTerm.get(Key, Default)

    # long term memory

    def RememberLong(self, Key, Value):
        self.DB.execute("""
            INSERT OR REPLACE INTO Keys(Key, Value)
            VALUES(?, ?)
        """, (Key, Value))
        self.DB.commit()

    def RecallLong(self, Key, Default=None):
        Row = self.DB.execute("SELECT Value FROM Keys WHERE Key=?", (Key,)).fetchone()
        return Row["Value"] if Row else Default

    async def RememberLong_async(self, Key, Value):
        await asyncio.to_thread(self.RememberLong, Key, Value)

    async def RecallLong_async(self, Key, Default=None):
        return await asyncio.to_thread(self.RecallLong, Key, Default)

    # syntax sugar

    def AddFact(self, text: str, Category="General"):
        self.train([text], Category)

    def AddFactPerm(self, text: str, Category="Permanent"):
        self.trainperm([text], Category)

    async def AddFact_async(self, text: str, Category="General"):
        await self.train_async([text], Category)

    async def AddFactPerm_async(self, text: str, Category="Permanent"):
        await self.trainperm_async([text], Category)
