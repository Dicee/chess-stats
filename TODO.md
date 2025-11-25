# TODO

## Jupyter notebook

- improve time control detection (average time rather than base time). Important when the increment is large (for example 2+15 is considered to be rapid by lichess.org because after 30 moves you have consumed up to 9m30s).
- use ECO code to get more precision on the specific opening played. Will have to join with a dataset that knows the name of each ECO code.
- filter top weaknesses to only those that have high enough volume
- ability to detect a common opening mistake by the user. Doesn't seem so easy to do but lichess has an option to share the evaluation in the PGN, which might be used to do this.

## Presentation layer

- would be nice to have an HTML page, or maybe directly in the Jupyter notebook but seems less flexible, allowing to add filters (e.g. date, ELO, time control), view the top openings and top opening weaknesses in a table and then being able to drill down in each one, with a separate page showing detailed performance in the opening for each line

# Done

## Game collection script

- validate end date is less than current date

