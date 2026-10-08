from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import psycopg
from psycopg import sql

from config import ACWR_HIGH, ACWR_LOW, DATABASE_URL

VIEWS_PATH = Path("sql/views.sql")
CHART_DIR = Path("outputs/charts")
TABLE_DIR = Path("outputs/tables")

PRIMARY = "#2a78d6"
SECONDARY = "#eb6834"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
GOOD = "#0ca30c"
WARNING = "#fab219"
CRITICAL = "#d03b3b"


def apply_views(conn):
    text = sql.SQL(VIEWS_PATH.read_text()).format(
        acwr_low=sql.Literal(ACWR_LOW),
        acwr_high=sql.Literal(ACWR_HIGH),
    )
    conn.execute(text)
    conn.commit()


def query(statement, params=None):
    with psycopg.connect(DATABASE_URL) as conn:
        apply_views(conn)
        cur = conn.execute(statement, params)
        columns = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def new_chart(title, xlabel, ylabel, size=(10, 5)):
    fig, ax = plt.subplots(figsize=size, facecolor="white")
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_title(title, loc="left", color=INK, fontsize=13, pad=12)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=10)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=10)
    return fig, ax


def legend(ax, **kwargs):
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, **kwargs)


def save_chart(fig, name):
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / name
    fig.savefig(path, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def save_table(df, name):
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLE_DIR / name
    df.to_csv(path, index=False)
    return path


def format_hms(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def format_hm(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}"


def format_ms(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"
