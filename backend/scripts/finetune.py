"""
KR-FinBert-SC Fine-tuning 스크립트

흐름:
  labeled_data.csv 로드
  → 텍스트(제목+본문) + 레이블 준비
  → train(80%) / val(20%) 분리
  → 토크나이징
  → Trainer로 fine-tune
  → ./finetuned_model/ 에 저장

실행: python finetune.py
"""

import csv
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)

# ── 설정 ─────────────────────────────────────────────────────────────
BASE_MODEL   = "snunlp/KR-FinBert-SC"
DATA_FILE    = Path(__file__).parent.parent / "labeled_data.csv"
OUTPUT_DIR   = Path(__file__).parent.parent / "finetuned_model"
MAX_LENGTH   = 256   # 토큰 최대 길이
EPOCHS       = 3
BATCH_SIZE   = 16
LEARNING_RATE = 2e-5

# KR-FinBert-SC 레이블 매핑 (pretrained 모델과 동일하게 맞춤)
LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
ID2LABEL = {0: "negative", 1: "neutral", 2: "positive"}


# ── 데이터 로드 ───────────────────────────────────────────────────────
def load_data(path: Path) -> tuple[list[str], list[int]]:
    texts, labels = [], []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label_str = row["label"].strip()
            if label_str not in LABEL2ID:
                continue
            title   = row.get("title", "").strip()
            text    = title
            label_id = LABEL2ID[label_str]
            texts.append(text)
            labels.append(label_id)
    return texts, labels


# ── PyTorch Dataset ───────────────────────────────────────────────────
# Trainer에 넣기 위한 최소한의 래핑
class FinDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels    = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


# ── 평가 지표 ─────────────────────────────────────────────────────────
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, preds)
    f1  = f1_score(labels, preds, average="macro")
    return {"accuracy": round(acc, 4), "f1_macro": round(f1, 4)}


# ── 메인 ─────────────────────────────────────────────────────────────
def main():
    print(f"데이터 로드: {DATA_FILE}")
    texts, labels = load_data(DATA_FILE)
    print(f"총 {len(texts)}개 | "
          f"긍정 {labels.count(2)} / 부정 {labels.count(0)} / 중립 {labels.count(1)}")

    # train / val 분리
    # stratify로 클래스 비율 유지, seed 고정해서 재현 가능하게
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"train {len(train_texts)}개 / val {len(val_texts)}개\n")

    # 토크나이저 로드
    print(f"토크나이저 로드: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    train_enc = tokenizer(train_texts, truncation=True, padding=True, max_length=MAX_LENGTH)
    val_enc   = tokenizer(val_texts,   truncation=True, padding=True, max_length=MAX_LENGTH)

    train_dataset = FinDataset(train_enc, train_labels)
    val_dataset   = FinDataset(val_enc,   val_labels)

    # 모델 로드
    print(f"모델 로드: {BASE_MODEL}\n")
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    # 학습 설정
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_steps=50,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        logging_steps=20,
        fp16=torch.cuda.is_available(),  # GPU 있으면 fp16 사용
        report_to="none",                # wandb 등 외부 로깅 끔
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    print("=" * 50)
    print("Fine-tuning 시작")
    print("=" * 50)
    trainer.train()

    # 최적 모델 저장
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"\n모델 저장 완료: {OUTPUT_DIR}")

    # 최종 검증 결과 출력
    results = trainer.evaluate()
    print(f"\n검증 결과:")
    print(f"  accuracy : {results['eval_accuracy']}")
    print(f"  f1_macro : {results['eval_f1_macro']}")


if __name__ == "__main__":
    main()
