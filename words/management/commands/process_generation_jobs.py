"""
Process pending async word generation jobs.

Run on a schedule (e.g. systemd timer) to execute queued AI word
generation requests instead of relying on short-lived background threads.
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from words.models import WordGenerationJob
from words.services.word_generation import (
    WordGenerationRequest,
    WordGenerationService,
)


class Command(BaseCommand):
    help = "Process pending WordGenerationJob queue entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=1,
            help="Maximum number of jobs to process per run (default: 1)",
        )

    def handle(self, *args, **options):
        max_jobs = options["max_jobs"]
        processed = 0

        job = (
            WordGenerationJob.objects.filter(status=WordGenerationJob.Status.PENDING)
            .select_related("user")
            .order_by("created_at")
            .first()
        )
        while job and processed < max_jobs:
            self._process(job)
            processed += 1
            job = (
                WordGenerationJob.objects.filter(status=WordGenerationJob.Status.PENDING)
                .select_related("user")
                .order_by("created_at")
                .first()
            )

        if processed:
            self.stdout.write(self.style.SUCCESS(f"Processed {processed} job(s)"))

    def _process(self, job: WordGenerationJob) -> None:
        self.stdout.write(f"Processing job {job.pk} for {job.user.username}")

        updated = WordGenerationJob.objects.filter(
            pk=job.pk, status=WordGenerationJob.Status.PENDING
        ).update(
            status=WordGenerationJob.Status.RUNNING,
            started_at=timezone.now(),
        )
        if not updated:
            return

        job.status = WordGenerationJob.Status.RUNNING
        result_key = f"gen_result_{job.user_id}"

        try:
            service = WordGenerationService()
            request_data = WordGenerationRequest(
                count=job.count,
                level=job.level,
                theme=job.theme or None,
                source=job.source,
            )
            used_model, generated_words = service.generate_words(request_data)

            if not generated_words:
                job.status = WordGenerationJob.Status.FAILED
                job.error = "Could not parse AI response."
                job.finished_at = timezone.now()
                job.save()
                cache.set(result_key, {"error": job.error}, timeout=300)
                return

            created, skipped = service.save_words(generated_words, job.source)
            result_data = {
                "word_ids": [w.id for w in created],
                "words_skipped": len(skipped),
                "model_used": used_model,
            }
            job.status = WordGenerationJob.Status.SUCCESS
            job.result = result_data
            job.finished_at = timezone.now()
            job.save()
            cache.set(result_key, result_data, timeout=300)
        except Exception as e:
            job.status = WordGenerationJob.Status.FAILED
            job.error = str(e)
            job.finished_at = timezone.now()
            job.save()
            cache.set(result_key, {"error": str(e)}, timeout=300)
            self.stderr.write(self.style.ERROR(f"Job {job.pk} failed: {e}"))
