# Alertas AWS — Parte 2

Monitor da previsão da Fase 2. O plano de execução está na raiz, em `PLANO-ACAO-ALERTAS-AWS.md`. O clique a clique do portal está em `PORTAL-AWS-TEMPORARIO.md`; apague esse arquivo antes da entrega final.

Na raiz do repositório:

```powershell
python -m unittest servicos/fase7-alertas-aws/test_regras.py -v
python servicos/fase7-alertas-aws/monitorar.py --arquivo servicos/fase7-alertas-aws/exemplo-previsao.json
python servicos/fase7-alertas-aws/monitorar.py --cidade "Irecê"
```

`--enviar` publica no SNS e só deve ser usado na EC2 de São Paulo, com `AWS_SNS_TOPIC_ARN` definido. Sem essa opção, o comando imprime o e-mail e não envia nada.
