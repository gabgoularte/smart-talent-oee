# Smart Talent John Deere 🚜

Projeto do tema Manufatura — Eficiência (OEE), desenvolvido em grupo durante o treinamento de computação aplicada à indústria (SQL, Python e Docker).

## Dataset

- **Fonte:** [Optimization of Machine Downtime (Kaggle)](https://www.kaggle.com/datasets/srinivasanusuri/optimization-of-machine-downtime)
- **Arquivo:** `Machine_Downtime.csv`
- **Volume:** 2.500 leituras, de 24/11/2021 a 03/07/2022 (164 dias distintos)
- **Estrutura:** 3 máquinas, 3 linhas de montagem (uma máquina por linha)
- **Conteúdo:** leituras de sensores (pressões, temperaturas, vibrações, rotação, tensão, torque e força de corte) e um indicador de parada (`Machine_Failure` / `No_Machine_Failure`)

## Estrutura do projeto

```text
smart-talent-oee/
├── data/
│   └── MachineDowntime.csv
├── src/
│   └── smart_talent_oee/
├── .gitignore
├── README.md
├── pyproject.toml
└── uv.lock
```
