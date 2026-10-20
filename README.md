# Backup GTI — protótipo

Faz cópias dos quatro CSVs configurados, sem modificar os originais. Usa somente a biblioteca padrão do Python em execução. `PrototipoV1.py` foi preservado como rascunho; o ponto de entrada agora é `main.py`.

## Configuração

Edite `config.json` em UTF-8. Origem, destino, arquivos, dias e horário são relidos a cada execução. Caminhos relativos são resolvidos a partir da pasta do JSON. No JSON, barras invertidas precisam ser duplicadas; caminhos locais podem usar `/`.

Os nomes configurados são atendimentos.csv, clientesAtendidos.csv, FatoProducao.csv e producoesReports.csv. A origem é a pasta de rede informada pelo usuário; destino é AmbinteTest_Backups.

Agenda inicial: segunda a sexta a partir das 10h, pelo relógio local do Windows. O Windows inicia uma verificação por minuto; o programa encerra imediatamente se não houver backup pendente. Pode haver atraso de aproximadamente um minuto, além de atrasos do próprio Windows.

Uma tentativa automática por dia. Falhas, arquivos ausentes e interrupções também consomem essa tentativa. O estado é gravado antes das cópias, para impedir repetição automática. Se a rede estiver indisponível ao entrar no Windows, será necessário repetir manualmente. Consultar logs antes de repetir.

Execução manual ignora dias/horário e o limite diário, substituindo as cópias do dia. Ela não consome a tentativa automática nem apaga seu registro. Um bloqueio impede duas execuções simultâneas usando o mesmo config/estado.

Se o computador ficar desligado vários dias, só é criado o backup do dia atual, se permitido pela agenda. Não são reconstruídos arquivos dos dias passados.

## Pastas e registros

Formato solicitado: `AmbinteTest_Backups/10.Outubro/16-10/arquivo.csv`. Os arquivos mantêm seus nomes. Uma cópia temporária só substitui o backup anterior após terminar; em caso de erro, a cópia anterior permanece. A leitura de arquivos alterados por outro processo durante a cópia não representa um snapshot transacional.

**O formato não contém ano. Antes de reutilizar no ano seguinte, arquive a pasta de backups ou ajuste o destino no JSON**, para não substituir o mesmo dia do ano anterior.

`logs/backup.log` registra resultados e erros (rotação de 2 MB, três arquivos anteriores). Verificações sem trabalho não enchem o log. `estado.json` é criado pelo programa; não edite nem exclua para uso normal. Estado inválido bloqueia a execução para evitar duplicidade. Use `--manual` para repetir backups.

## Executar com Python

Abra um terminal na pasta do projeto, usando uma instalação funcional de Python 3.10 ou superior:

```powershell
python main.py --validar
python -m unittest -v test_backup
python main.py
python main.py --manual
```

`--validar` verifica apenas a configuração, sem acessar a origem. Sem argumentos, verifica a agenda e pode executar o backup real. `--manual` copia imediatamente. `--config "caminho/config.json"` permite usar outra configuração; log, estado e bloqueio ficam ao lado desse JSON.

Códigos de saída: 0 = sucesso ou nada a fazer; 1 = backup com falhas; 2 = erro de configuração/estado/inicialização.

## Gerar executável

No Python de desenvolvimento, instale PyInstaller e execute:

```powershell
python -m pip install pyinstaller
.\gerar_exe.ps1
```

Para indicar outro Python: `.\gerar_exe.ps1 -Python 'C:/caminho/python.exe'`.

O script cria `BackupGTI.exe` ao lado do `config.json`. Distribua ambos juntos em uma pasta com permissão de escrita, para que estado e logs sejam salvos. O computador de destino não precisa de Python. Mudanças no JSON não exigem recompilar; alterações no código exigem gerar outro executável. Não inclua config.json dentro do executável como única cópia.

## Ativar no Windows

Depois de gerar o executável, execute nesta pasta:

```powershell
.\instalar_agendamento.ps1
```

Isso cadastra `GTI - Backup de CSVs`, com verificação a cada minuto e ao entrar na conta. O script não substitui uma tarefa já existente. Pode ser necessário que a TI permita o cadastro de tarefas conforme as políticas da máquina.

O cadastro usa a conta atual, sem armazenar senha, e executa **somente enquanto essa conta estiver conectada ao Windows**, inclusive com a tela bloqueada. Ao ligar, entre na conta e tenha acesso à rede corporativa. Executar antes do login exigiria outro modelo de credenciais/agendamento, não incluído neste protótipo.

Para desativar ou remover, abra o Agendador de Tarefas e localize o nome acima. A criação do código e os testes não cadastram a tarefa automaticamente.

Os testes usam CSVs fictícios e pastas temporárias. Não validam a permissão real ao compartilhamento corporativo.
