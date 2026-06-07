import json
import os
from django.conf import settings
from django.core.management import BaseCommand
from app01.models import Problems


class Command(BaseCommand):
    help = 'Load programming problems from JSON file'

    def handle(self, *args, **kwargs):
        # 使用 settings.BASE_DIR 来构建一个绝对路径
        json_file_path = os.path.join(settings.BASE_DIR, 'json', 'valid23k.json')

        self.stdout.write(f"Attempting to open file: {json_file_path}")

        with open(json_file_path, 'r', encoding='utf-8') as file:
            problems = json.load(file)
            for problem in problems:
                Problems.objects.create(
                    id=problem['id'],
                    desc=problem['original_text'],
                    equation=problem['equation'],
                    segmented_text=problem['segmented_text']
                )
        self.stdout.write(self.style.SUCCESS('Successfully loaded problems'))
