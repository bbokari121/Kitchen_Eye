# Kitchen Eye

A desktop application that detects kitchen objects in real time and announces them via text-to-speech — supporting multiple languages.

## Repository Structure

```
Kitchen_Eye/
├── app/                     # Desktop application (main product)
│   ├── main.py              # Entry point
│   ├── ui/                  # Window and UI components
│   ├── inference/           # Detection + preprocessing
│   ├── audio/               # TTS and translation
│   └── utils/               # Config loader
├── models/                  # Final exported weights (committed)
│   ├── yolo/best.pt
│   └── frcnn/best.pth
├── notebooks/               # Data preparation notebooks
│   ├── setup_code.ipynb
│   ├── split_coco_json.ipynb
│   └── split_labels.ipynb
├── data/                    # Raw / split dataset (git-ignored)
└── training_models/         # Experiment notebooks (git-ignored)
```

## Quickstart

```bash
python app/main.py
```

## Models

| Model | Weights |
|-------|---------|
| YOLOv8 | `models/yolo/best.pt` |
