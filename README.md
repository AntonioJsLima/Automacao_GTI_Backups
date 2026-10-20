Backup GTI
Automação de cópias de segurança de arquivos CSV utilizados pela área de GTI. O sistema copia arquivos de uma origem configurada para um destino organizado por mês e dia, mantendo os arquivos originais sem alteração.
O que o projeto faz
O projeto permite configurar quais arquivos serão copiados, as pastas de origem e destino e os dias e horário para as tentativas automáticas. A configuração é mantida em um arquivo JSON externo, permitindo ajustar esses parâmetros sem alterar o código.
Na configuração atual, são definidos quatro arquivos CSV: atendimentos.csv, clientesAtendidos.csv, FatoProducao.csv e producoesReports.csv.
Como funciona
Em cada verificação, a aplicação consulta a configuração e o estado das tentativas anteriores. Se o dia e o horário permitirem uma tentativa, cria a pasta correspondente à data no destino e copia cada arquivo configurado.
A estrutura de destino segue o formato mês/dia, por exemplo:
10.Outubro/
└── 16-10/
    ├── atendimentos.csv
    ├── clientesAtendidos.csv
    ├── FatoProducao.csv
    └── producoesReports.csv
A aplicação copia os arquivos como estão, sem interpretar ou transformar o conteúdo dos CSVs. Cada cópia é preparada em um arquivo temporário e só substitui uma cópia existente quando a transferência termina. Uma falha em um arquivo é registrada e não impede a tentativa de copiar os demais.
O estado da execução é persistido para limitar as tentativas automáticas a uma por dia. O sistema também mantém um bloqueio para evitar execuções simultâneas e registra resultados e erros em log, com rotação dos arquivos de log.
Componentes
- main.py: valida a configuração, verifica a agenda, coordena a execução e registra o estado.
- backup.py: realiza as cópias dos arquivos e organiza o destino por data.
- config.json: define origem, destino, arquivos e agenda.
- test_backup.py: contém testes automatizados com arquivos fictícios e diretórios temporários.
Tecnologias e cuidados
O projeto foi desenvolvido em Python e utiliza recursos da biblioteca padrão. A configuração atual aponta para uma origem em compartilhamento de rede e um destino em unidade de armazenamento.
A organização do destino não inclui o ano. Ao manter backups por mais de um ano na mesma pasta, vale considerar essa característica ao planejar a retenção dos arquivos.
