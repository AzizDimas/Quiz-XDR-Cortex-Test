import json
import random
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Cortex XDR Analyst Quiz", page_icon="🛡️", layout="centered")

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
LETTERS = "ABCDEF"


@st.cache_data
def load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


Q = load_questions()
CATS = sorted({q["cat"] for q in Q})


# ---------- state ----------
def init_state():
    defaults = {
        "phase": "setup",  # setup | play | result
        "deck": [],
        "i": 0,
        "score": 0,
        "log": [],
        "checked": False,
        "last_pick": [],
        "run": 0,  # bump supaya widget key selalu fresh
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def begin(deck):
    st.session_state.update(
        phase="play", deck=deck, i=0, score=0, log=[], checked=False, last_pick=[]
    )
    st.session_state.run += 1


def finish():
    st.session_state.phase = "result"


def go_setup():
    st.session_state.phase = "setup"


def next_question():
    st.session_state.i += 1
    st.session_state.checked = False
    st.session_state.last_pick = []
    if st.session_state.i >= len(st.session_state.deck):
        finish()


init_state()

st.title("🛡️ Cortex XDR Analyst Quiz")

# ---------- setup ----------
if st.session_state.phase == "setup":
    st.caption(f"{len(Q)} soal, jawaban tunggal dan multi-select, ada penjelasan")
    with st.container(border=True):
        cat = st.selectbox("Category", ["Semua"] + CATS, format_func=lambda c: f"Semua ({len(Q)})" if c == "Semua" else f"{c} ({sum(q['cat'] == c for q in Q)})")
        mode = st.selectbox("Mode", ["Random shuffle", "Urut nomor"])
        pool = [q for q in Q if cat == "Semua" or q["cat"] == cat]
        cnt = st.number_input("Jumlah soal", min_value=1, max_value=len(pool), value=min(20, len(pool)), step=1)
        if st.button("Mulai", type="primary", use_container_width=True):
            deck = pool.copy()
            if mode == "Random shuffle":
                random.shuffle(deck)
            begin(deck[: int(cnt)])
            st.rerun()

# ---------- play ----------
elif st.session_state.phase == "play":
    deck, i = st.session_state.deck, st.session_state.i
    q = deck[i]
    multi = len(q["a"]) > 1

    c1, c2 = st.columns(2)
    c1.caption(f"Soal {i + 1} / {len(deck)} (#{q['n']})")
    c2.caption(f"Benar: {st.session_state.score}")
    st.progress(i / len(deck))

    with st.container(border=True):
        st.caption(q["cat"] + (f" | pilih {len(q['a'])}" if multi else ""))
        st.markdown(f"**{q['q']}**")

        if not st.session_state.checked:
            key = f"w_{st.session_state.run}_{i}"
            labels = [f"{LETTERS[k]}. {t}" for k, t in enumerate(q["o"])]
            picked = []
            if multi:
                for k, lab in enumerate(labels):
                    if st.checkbox(lab, key=f"{key}_{k}"):
                        picked.append(LETTERS[k])
            else:
                choice = st.radio("Pilih jawaban", labels, index=None, key=key, label_visibility="collapsed")
                if choice:
                    picked = [choice[0]]

            if st.button("Cek jawaban", type="primary", disabled=not picked, use_container_width=True):
                ok = sorted(picked) == sorted(q["a"])
                if ok:
                    st.session_state.score += 1
                st.session_state.log.append({"q": q, "ok": ok, "pick": "".join(sorted(picked))})
                st.session_state.last_pick = picked
                st.session_state.checked = True
                st.rerun()
        else:
            picked = st.session_state.last_pick
            for k, t in enumerate(q["o"]):
                L = LETTERS[k]
                text = f"**{L}.** {t}"
                if L in q["a"]:
                    st.success(text)
                elif L in picked:
                    st.error(text)
                else:
                    st.markdown(f"&nbsp;&nbsp;{text}")

            ok = st.session_state.log[-1]["ok"]
            st.info(("Benar. " if ok else "Salah. ") + "Jawaban: " + ", ".join(q["a"]) + "\n\n" + q["e"])

            last = i + 1 >= len(deck)
            if st.button("Lihat hasil" if last else "Lanjut", type="primary", use_container_width=True):
                next_question()
                st.rerun()

    if st.button("Stop dan lihat hasil"):
        finish()
        st.rerun()

# ---------- result ----------
else:
    log = st.session_state.log
    score = st.session_state.score
    n = len(log)
    pct = round(score / n * 100) if n else 0
    bad = [x for x in log if not x["ok"]]

    with st.container(border=True):
        st.caption("Hasil")
        st.markdown(f"## {score} / {n}")
        st.caption(f"{pct}%")
        c1, c2 = st.columns(2)
        if c1.button("Main lagi", type="primary", use_container_width=True):
            go_setup()
            st.rerun()
        if c2.button("Ulang yang salah", disabled=not bad, use_container_width=True):
            deck = [x["q"] for x in bad]
            random.shuffle(deck)
            begin(deck)
            st.rerun()

    with st.container(border=True):
        st.caption(f"Yang salah ({len(bad)})")
        for x in bad:
            st.markdown(
                f"**#{x['q']['n']}** {x['q']['q']}  \n"
                f"kamu: `{x['pick']}` | benar: `{''.join(x['q']['a'])}`"
            )
            st.divider()
