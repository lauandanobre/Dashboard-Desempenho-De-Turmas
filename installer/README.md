# Instalador (Windows)

Passo a passo completo para gerar o executavel e o instalador. Nada disso e necessario para quem so vai *usar* o programa.

1. **Executavel:** de dois cliques em `build_windows.bat` (na raiz do projeto). Ele cria o ambiente, roda os testes e gera `dist\MetricasDasTurmas\MetricasDasTurmas.exe`.
2. **Instalador (opcional):** instale o [Inno Setup 6](https://jrsoftware.org/isdl.php) (gratuito), abra `installer\instalador.iss` e aperte **F9**. Resultado: `dist_instalador\Instalador_Metricas_das_Turmas.exe`.
3. **Automatico:** o workflow `.github/workflows/build-windows.yml` faz os dois passos no GitHub e publica o instalador em *Releases* (veja o README principal).
