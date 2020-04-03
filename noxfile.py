import nox

@nox.session
def tests(session):
    session.install('pytest')
    session.install('.[test]')
    session.run('pytest', 'tests')

@nox.session
def lint(session):
    session.install('black')
    session.install('flake8')
    session.run('black', '--check', '.')
    session.run('flake8', 'src', 'tests')