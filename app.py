import sqlite3, random, streamlit as st, pandas as pd, altair as alt, datetime as dt

DB = "data/theory.db"
conn = sqlite3.connect(DB, check_same_thread=False)

# --- sidebar ---
st.sidebar.title("🎓 Theory-Trainer")
cats = [r[0] for r in conn.execute("SELECT DISTINCT category FROM concepts")]
use_cats = st.sidebar.multiselect("Choose categories", cats, default=cats)
quiz_len = st.sidebar.slider("Questions per round", 3, 10, 5)
if "points" not in st.session_state: st.session_state.update(points=0, streak=0)

# --- helpers ---
def pick_q():
    rows = conn.execute("SELECT id,concept,definition FROM concepts WHERE category IN ({})"
                        .format(",".join("?"*len(use_cats))), use_cats).fetchall()
    target = random.choice(rows)
    distract = random.sample([r for r in rows if r!=target], k=4)
    choices = random.sample([target]+distract, k=5)
    return target, choices

def record_result(cid, correct):
    conn.execute("""CREATE TABLE IF NOT EXISTS stats(
                       concept_id INT, date DATE,
                       attempts INT, correct INT)""")
    conn.execute("""INSERT INTO stats VALUES(?,?,1,?)""",
                 (cid, dt.date.today(), 1 if correct else 0))
    conn.commit()

# --- main ---
st.header("🚀 Quick Quiz")
for qn in range(quiz_len):
    target, choices = pick_q()
    st.subheader(f"Q{qn+1}. Which *concept* matches this definition?")
    st.markdown(f"> *{target[2]}*")
    picked = st.radio("", [c[1] for c in choices], key=f"q{qn}")
    if st.button("Lock in", key=f"b{qn}"):
        correct = (picked == target[1])
        st.success("Correct! 🎉") if correct else st.error(
            f"Oops. Answer: **{target[1]}**")
        # scoring
        if correct:
            st.session_state.streak += 1
            st.session_state.points += 10 * (1 + 0.2*st.session_state.streak)
        else:
            st.session_state.streak = 0
        record_result(target[0], correct)

st.info(f"**Score**: {int(st.session_state.points)} | "
        f"**Current streak**: {st.session_state.streak}")

# --- analytics ---
st.header("📊 Trouble Spots")
df = pd.read_sql("""SELECT c.concept, c.category,
                           SUM(s.attempts) AS seen,
                           SUM(s.correct)  AS hit
                    FROM stats s JOIN concepts c ON c.id=s.concept_id
                    GROUP BY c.id""", conn)

if not df.empty:
    df["miss_pct"] = 1 - df["hit"]/df["seen"]
    worst = df.sort_values("miss_pct", ascending=False).head(10)
    st.subheader("Most-missed definitions")
    st.table(worst[["concept","category","miss_pct"]].style.format({"miss_pct":"{:.0%}"}))

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("concept:N", sort="-y", title="Concept"),
        y=alt.Y("miss_pct:Q", title="% wrong"),
        color="category"
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)
else:
    st.write("Play a round first to see analytics!")

