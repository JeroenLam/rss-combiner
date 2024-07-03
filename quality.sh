poetry run pyupgrade $(find * -type f -regex ".*.pyi?") --py311-plus
poetry run pycln --all --expand-stars  --extend-exclude tests --extend-exclude pynicillium_output .
poetry run isort --profile=black .
poetry run black .
poetry run mypy --strict --follow-imports=skip --exclude data --exclude pynicillium_output --exclude tests .
