def sure_jar(name: str) -> str:
    return name if name.endswith('.jar') else f'{name}.jar'
