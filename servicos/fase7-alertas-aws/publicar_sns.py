"""Publicação no tópico SNS. Só roda quando o monitor recebe --enviar."""

import os


def publicar(alerta, _local, *, assunto, corpo):
    arn = os.environ.get("AWS_SNS_TOPIC_ARN", "").strip()
    if not arn:
        raise RuntimeError("Defina AWS_SNS_TOPIC_ARN com o ARN do tópico em sa-east-1.")
    regiao = os.environ.get("AWS_DEFAULT_REGION", "sa-east-1").strip() or "sa-east-1"
    if ":sa-east-1:" not in arn:
        raise RuntimeError("O tópico precisa estar na região sa-east-1, a mesma da Fase 5.")
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise RuntimeError("Instale boto3 nesta máquina antes de usar --enviar.") from exc

    cliente = boto3.client("sns", region_name=regiao)
    try:
        resposta = cliente.publish(TopicArn=arn, Subject=assunto, Message=corpo)
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError("Não foi possível publicar no tópico SNS.") from exc
    message_id = resposta.get("MessageId")
    if not isinstance(message_id, str) or not message_id:
        raise RuntimeError("O SNS não confirmou o identificador da mensagem.")
    return message_id
