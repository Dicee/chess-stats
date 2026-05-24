import re
import argparse
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, ALL, callback_context

from dash.exceptions import PreventUpdate


def _format_line(path_moves):
    """Format a ply list ['e4','e5','Nf3'] into '1. e4 e5 2. Nf3'."""
    path_moves = list(path_moves or [])
    if not path_moves:
        return ""
    parts = []
    for i in range(0, len(path_moves), 2):
        move_no = i // 2 + 1
        w = path_moves[i]
        b = path_moves[i + 1] if i + 1 < len(path_moves) else None
        if b is None:
            parts.append(f"{move_no}. {w}")
        else:
            parts.append(f"{move_no}. {w} {b}")
    return " ".join(parts)


# ----------------------------
# Data loading & parsing
# ----------------------------
DEFAULT_DATA_PATH = None
app = Dash(__name__)


def _load_base_df(file_path=None):
    """Load required columns from a CSV/TSV file path."""
    columns = ["game_moves", "result", "opening_family", "opening_name"]
    if not file_path:
        raise ValueError("Missing games file path. Pass --games /path/to/file.tsv")

    path_lower = str(file_path).lower()
    sep = "\t" if path_lower.endswith(".tsv") or path_lower.endswith(".tab") else ","
    return pd.read_csv(file_path, usecols=columns, sep=sep)



SAN_REGEX = re.compile(r"\d+\.(\.\.)?\s*")


def _tokenize_moves(moves_str: str):
    """Tokenize a 'game_moves' string like: '1.e4 e5 2.Nf3 d5 ...' into SAN tokens.

    This is intentionally permissive; we strip move numbers and split on whitespace.
    """
    if moves_str is None or (isinstance(moves_str, float) and pd.isna(moves_str)):
        return []
    s = str(moves_str).strip()
    if not s:
        return []
    s = SAN_REGEX.sub("", s)
    # Remove common game-end markers (if present)
    s = s.replace("1-0", "").replace("0-1", "").replace("1/2-1/2", "").replace("*", "")
    toks = [t.strip() for t in s.split() if t.strip()]
    return toks


def _result_to_outcome(result_str: str):
    """Map result to outcome from White perspective."""
    if result_str == "1-0":
        return "W"
    if result_str == "0-1":
        return "B"
    if result_str == "1/2-1/2":
        return "D"
    return None


def _next_move_index(path_len: int, player: str):
    # Deprecated helper kept for backwards compatibility with earlier iterations.
    return path_len



def compute_position_stats(records, path_moves, top_n: int = 30):
    """Compute next-move stats + opening info for a given prefix path.

    Opening logic:
      - consider all games matching the prefix sequence
      - pick the most frequent opening_family among them
      - if, within that family, there is exactly one unique opening_name, display it
    """
    path_moves = list(path_moves or [])
    path_len = len(path_moves)

    move_counts = Counter()
    outcomes = {}  # per move: counts of W/B/D outcomes

    family_counts = Counter()
    names_by_family = {}
    matched = 0

    for rec in records:
        toks = rec.get("_tokens", [])
        if toks[:path_len] != path_moves:
            continue

        matched += 1

        fam = rec.get("opening_family")
        if fam:
            family_counts[fam] += 1
            if fam not in names_by_family:
                names_by_family[fam] = set()
            nm = rec.get("opening_name")
            if nm:
                names_by_family[fam].add(nm)

        # Next move (if any)
        if len(toks) <= path_len:
            continue
        mv = toks[path_len]
        move_counts[mv] += 1

        oc = _result_to_outcome(rec.get("result"))
        if oc is None:
            continue
        if mv not in outcomes:
            outcomes[mv] = {"W": 0, "B": 0, "D": 0}
        outcomes[mv][oc] += 1

    top_family = None
    top_opening_name = None
    if family_counts:
        top_family = family_counts.most_common(1)[0][0]
        names = {n for n in names_by_family.get(top_family, set()) if n}
        if len(names) == 1:
            top_opening_name = list(names)[0]

    rows = []
    for mv, n in move_counts.most_common(top_n):
        oc = outcomes.get(mv, {"W": 0, "B": 0, "D": 0})
        total = max(n, 1)
        w_pct = 100.0 * oc["W"] / total
        b_pct = 100.0 * oc["B"] / total
        d_pct = 100.0 * oc["D"] / total
        rows.append(
            {
                "move": mv,
                "games": int(n),
                "white_win_pct": w_pct,
                "black_win_pct": b_pct,
                "draw_pct": d_pct,
            }
        )

    return pd.DataFrame(rows), matched, top_family, top_opening_name




def make_win_gauge(white_win_pct: float, black_win_pct: float, draw_pct: float):
    """Stacked horizontal bar with % labels directly on the bar."""
    w = max(0.0, min(100.0, float(white_win_pct)))
    b = max(0.0, min(100.0, float(black_win_pct)))
    d = max(0.0, min(100.0, float(draw_pct)))

    # normalize in case rounding made it not sum to 100
    s = w + b + d
    if s > 0:
        w, d, b = (100.0 * w / s, 100.0 * d / s, 100.0 * b / s)

    fig = go.Figure()

    # Only show text if the segment is large enough to fit
    w_txt = f"{w:.1f}%" if w >= 6 else ""
    d_txt = f"{d:.1f}%" if d >= 6 else ""
    b_txt = f"{b:.1f}%" if b >= 6 else ""

    fig.add_trace(
        go.Bar(
            x=[w],
            y=[""],
            orientation="h",
            marker_color="#f0f0f0",
            text=[w_txt],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="#000000", size=12),
            hovertemplate=f"White win: {w:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=[d],
            y=[""],
            orientation="h",
            marker_color="#b0b0b0",
            text=[d_txt],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="#000000", size=12),
            hovertemplate=f"Draw: {d:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=[b],
            y=[""],
            orientation="h",
            marker_color="#202020",
            text=[b_txt],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="#ffffff", size=12),
            hovertemplate=f"Black win: {b:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="stack",
        height=28,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis=dict(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# Inject CSS in the app index (more reliable than rendering <style> in components
# across DSS/Dash bundles)
app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css" />
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js"></script>
    <style>
      .btn {
        font-size: 13px;
        padding: 8px 12px;
        border-radius: 10px;
        border: 1px solid rgba(0,0,0,0.18);
        background: #ffffff;
        color: #111827;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
        transition: filter 120ms ease-in-out, transform 20ms ease-in-out, box-shadow 120ms ease-in-out;
      }
      .btn:hover {
        filter: brightness(0.94);
        box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      }
      .btn:active {
        transform: translateY(1px);
      }
      .btn:focus {
        outline: none;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.25);
      }

      .btn-primary {
        background: #2563eb;
        border-color: #1d4ed8;
        color: #ffffff;
      }

      .btn-secondary {
        background: #ffffff;
      }

      .move-btn {
        width: 100%;
        text-align: left;
        padding: 6px 10px;
        border-radius: 10px;
        border: 1px solid rgba(0,0,0,0.10);
        background: #ffffff;
        cursor: pointer;
        transition: background 120ms ease-in-out, filter 120ms ease-in-out, box-shadow 120ms ease-in-out;
      }
      .move-btn:hover {
        filter: brightness(0.96);
        box-shadow: 0 1px 6px rgba(0,0,0,0.08);
      }
      .move-btn:active {
        filter: brightness(0.92);
      }

      .board-panel {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 10px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        width: fit-content;
      }

      #board-canvas {
        width: min(76vw, 520px);
      }

      .board-caption {
        margin-top: 8px;
        color: #6b7280;
        font-size: 12px;
      }

      .main-grid {
        display: grid;
        grid-template-columns: 560px minmax(420px, 1fr);
        gap: 16px;
        align-items: start;
      }

      @media (max-width: 1100px) {
        .main-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
"""

app.layout = html.Div(
    style={"fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", "padding": "12px"},
    children=[
        html.H2("Chess Line Explorer", style={"margin": "0 0 8px 0"}),
        html.Div(
            style={"display": "flex", "gap": "12px", "alignItems": "center", "flexWrap": "wrap"},
            children=[
                html.Button("Reset to start", id="reset-btn", n_clicks=0, className="btn btn-primary"),
                html.Button("Back 1 move", id="back-btn", n_clicks=0, className="btn btn-secondary"),
                html.Div(id="status", style={"fontSize": "12px", "color": "#666"}),
            ],
        ),
        html.Hr(),
        dcc.Store(id="path-store", data=[]),
        dcc.Store(id="base-data-store"),
        dcc.Interval(id="init", interval=200, n_intervals=0, max_intervals=1),
        html.Div(
            className="main-grid",
            children=[
                html.Div(
                    children=[
                        html.Div("Board", style={"fontSize": "12px", "color": "#666"}),
                        html.Div(
                            className="board-panel",
                            children=[
                                html.Div(id="board-canvas"),
                                html.Div(id="board-status", className="board-caption"),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Div("Moves", style={"fontSize": "12px", "color": "#666"}),
                        html.Div(id="current-line", style={"fontSize": "16px", "marginBottom": "6px"}),
                        html.Div(id="side-to-play", style={"fontSize": "12px", "color": "#666", "marginBottom": "4px"}),
                        html.Div(id="opening-info", style={"fontSize": "12px", "color": "#666", "marginBottom": "10px"}),
                        html.Div(
                            "Top next moves (click a move to go deeper)",
                            style={"fontSize": "12px", "color": "#666"},
                        ),
                        html.Div(
                            id="moves-list",
                            style={
                                "maxHeight": "70vh",
                                "overflowY": "auto",
                                "border": "1px solid #eee",
                                "borderRadius": "6px",
                                "padding": "8px",
                            },
                        ),
                    ]
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("base-data-store", "data"),
    Output("status", "children"),
    Input("init", "n_intervals"),
)
def load_data(_):
    # Load once per app session
    df = _load_base_df(DEFAULT_DATA_PATH)
    df["_tokens"] = df["game_moves"].apply(_tokenize_moves)
    # Keep only useful columns for serialization
    slim = df[["result", "_tokens", "opening_family", "opening_name"]].to_dict(orient="records")
    return slim, f"Loaded {len(df):,} game" + ("s" if len(df) > 1 else "")    




@app.callback(
    Output("path-store", "data"),
    Input("reset-btn", "n_clicks"),
    Input("back-btn", "n_clicks"),
    State("path-store", "data"),
    prevent_initial_call=True,
)
def reset_or_back(_, __, path):
    trg = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else None
    path = list(path or [])

    if trg == "reset-btn":
        return []
    if trg == "back-btn":
        return path[:-1] if len(path) > 0 else []

    raise PreventUpdate



@app.callback(
    Output("current-line", "children"),
    Output("side-to-play", "children"),
    Output("opening-info", "children"),
    Output("moves-list", "children"),
    Input("path-store", "data"),
    Input("base-data-store", "data"),
)
def render(path, base_data):


    path = path or []
    if not base_data:
        return "", "", "", html.Div("Loading data…")

    records = base_data

    # Next player is determined by ply parity
    next_player = "White" if (len(path) % 2 == 0) else "Black"

    # Next move stats + opening info
    stats, matched, top_family, top_opening_name = compute_position_stats(records, path, top_n=50)

    moves_so_far = _format_line(path)
    current_line = "Start position" if len(path) == 0 else moves_so_far
    side_to_play = f"Next to play: {next_player}"

    if top_family:
        opening_info = f"Opening: {top_family}" + (f" — {top_opening_name}" if top_opening_name else "")
    else:
        opening_info = "Opening: (unknown)"

    if stats.empty:
        return current_line, side_to_play, opening_info, html.Div("No game match this line.")

    items = []
    for i, row in stats.iterrows():
        mv = row["move"]
        games = int(row["games"])
        w = float(row["white_win_pct"])
        b = float(row["black_win_pct"])
        d = float(row["draw_pct"])

        fig = make_win_gauge(w, b, d)

        items.append(
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "140px 90px 1fr",
                    "gap": "10px",
                    "alignItems": "center",
                    "padding": "6px 4px",
                    "borderBottom": "1px solid #f2f2f2",
                },
                children=[
                    html.Button(
                        mv,
                        id={"type": "move-btn", "index": mv},
                        n_clicks=0,
                        className="move-btn",
                    ),


                    html.Div(f"{games:,} game" + ("s" if games > 1 else "") , style={"fontSize": "12px", "color": "#666"}),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                ],
            )

        )

    return current_line, side_to_play, opening_info, html.Div(items)




@app.callback(
    Output("path-store", "data", allow_duplicate=True),
    Input({"type": "move-btn", "index": ALL}, "n_clicks"),
    State({"type": "move-btn", "index": ALL}, "id"),
    State("path-store", "data"),
    prevent_initial_call=True,
)
def on_move_click(n_clicks_list, ids, path):
    if not n_clicks_list or not ids:
        raise PreventUpdate

    # find most recently clicked: take max n_clicks
    max_clicks = max(n_clicks_list)
    if max_clicks <= 0:
        raise PreventUpdate


    idx = n_clicks_list.index(max_clicks)
    mv = ids[idx]["index"]

    path = list(path or [])
    path.append(mv)
    return path


app.clientside_callback(
    """
    function(path) {
        try {
            if (typeof Chess === "undefined" || typeof Chessboard === "undefined") {
                return "Board libraries not loaded";
            }

            if (!window.__lineExplorerBoard) {
                const pieceGlyph = {
                    wK: "♔", wQ: "♕", wR: "♖", wB: "♗", wN: "♘", wP: "♙",
                    bK: "♚", bQ: "♛", bR: "♜", bB: "♝", bN: "♞", bP: "♟"
                };

                function pieceSvgDataUri(piece) {
                    const glyph = pieceGlyph[piece] || "?";
                    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">
  <rect width="80" height="80" fill="transparent"/>
  <text x="50%" y="56%" text-anchor="middle" dominant-baseline="middle"
        font-size="60" font-family="Segoe UI Symbol, Noto Sans Symbols, Arial Unicode MS, serif">${glyph}</text>
</svg>`;
                    return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
                }

                window.__lineExplorerBoard = Chessboard("board-canvas", {
                    draggable: false,
                    showNotation: true,
                    position: "start",
                    pieceTheme: pieceSvgDataUri
                });
            }

            const chess = new Chess();
            for (const mv of (path || [])) {
                const ok = chess.move(mv, { sloppy: true });
                if (!ok) {
                    window.__lineExplorerBoard.position(chess.fen(), false);
                    return "Stopped at invalid SAN: " + mv;
                }
            }
            const fen = chess.fen();
            window.__lineExplorerBoard.position(fen, false);
            return "FEN: " + fen;
        } catch (e) {
            return "Board unavailable";
        }
    }
    """,
    Output("board-status", "children"),
    Input("path-store", "data"),
)


def main():
    parser = argparse.ArgumentParser(description="Run chess line explorer")
    parser.add_argument("--games", dest="games_file_path", help="Path to CSV or TSV data file", required=True)
    parser.add_argument("--host", default="127.0.0.1", help="Dash server host")
    parser.add_argument("--port", type=int, default=8050, help="Dash server port")
    parser.add_argument("--debug", action="store_true", help="Enable Dash debug mode")
    args = parser.parse_args()

    global DEFAULT_DATA_PATH
    DEFAULT_DATA_PATH = args.games_file_path
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
