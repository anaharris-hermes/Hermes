@rem Hermes lemma-layer rebuild wrapper.
@rem Runs the Python CLI command `rebuild-lemmas` against the project source.
@rem Any arguments passed to this .cmd are forwarded to the Python CLI.
@echo off
python "%~dp0..\src\Hermes.LemmaBuilder\build_morphology.py" %*
