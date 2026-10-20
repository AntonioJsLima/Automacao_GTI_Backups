# Backup GTI

Automação de cópias de segurança de arquivos CSV utilizados pela área de GTI. O sistema copia arquivos de uma origem configurada para um destino organizado por mês e dia, mantendo os arquivos originais sem alteração.

## O que o projeto faz

A aplicação permite configurar:

- Pastas de origem e destino;
- Arquivos CSV que serão copiados;
- Dias da semana e horário das tentativas automáticas.

Essas opções ficam em um arquivo JSON externo, permitindo ajustar a configuração sem alterar o código.

Na configuração atual, são definidos quatro arquivos:

- `atendimentos.csv`
- `clientesAtendidos.csv`
- `FatoProducao.csv`
- `producoesReports.csv`

## Como funciona

Em cada verificação, a aplicação consulta a configuração e o estado das tentativas anteriores. Quando o dia e o horário permitem uma tentativa, o sistema cria a pasta correspondente à data no destino e copia cada arquivo configurado.

A estrutura de destino segue o formato `mês/dia`:

```text
10.Outubro/
└── 16-10/
    ├── atendimentos.csv
    ├── clientesAtendidos.csv
    ├── FatoProducao.csv
    └── producoesReports.csv
