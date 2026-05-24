# chess-stats
A simple set of scripts to collect chess games from lichess.org and chess.com and make some analysis on opening performance. To go quicker, I'll use some AI to generate the scripts and won't pay too much attention to code quality, I just want to have a tool to analyze my openings and maybe help other people to do the same.

## Project structure
- `scape-chess-com-openings.js`: allowed me to produce `chess-com-openings.tsv` by running it in my browser on chess.com's opening book page. The other two datasets had too many gaps so I had to do this to fill them.
- `analysis.ipynb`: this Jupyter notebook contains a simple data pipeline which reconciles 3 opening datasets and then joins them with games with the best possible accuracy (most precise opening line). It also generates a few charts to help identify top opening weaknesses, best played lines etc.
- `game_explorer.py`: Dash app allowing to explore the games (after they've been joined with openings by the notebook). It's similar to chess.com's opening explorer, except that it runs exclusively on the games from a local file, and of course it has much fewer features.
<img width="1475" height="679" alt="image" src="https://github.com/user-attachments/assets/d940a9b7-8a93-4699-a8ae-d5fb3171f820" />

## Useful links 

- API documentation
    - https://www.postman.com/team-zouhair/chess-analyse/documentation/q50kqzo/chess-com-api
    - https://lichess.org/api#tag/Games/operation/apiUserCurrentGame
- Opening banks
    - https://www.kaggle.com/datasets/alexandrelemercier/all-chess-openings
    - https://github.com/tomgp/chess-canvas/blob/master/pgn/chess_openings.csv

