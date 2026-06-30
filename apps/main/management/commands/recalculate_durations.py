import datetime
from django.core.management.base import BaseCommand
from apps.main.models import MeditationSteps
from apps.ai_service.tts import get_audio_duration


class Command(BaseCommand):
    help = 'Recalculates the actual audio file durations for all meditation steps.'

    def handle(self, *args, **options):
        steps = MeditationSteps.objects.exclude(audio_file='').exclude(audio_file__isnull=True)
        total_steps = steps.count()
        self.stdout.write(f"Found {total_steps} steps with audio files to process.")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for step in steps:
            try:
                # Open the associated file
                if not step.audio_file:
                    skipped_count += 1
                    continue

                try:
                    step.audio_file.open('rb')
                    audio_bytes = step.audio_file.read()
                finally:
                    step.audio_file.close()

                measured_seconds = get_audio_duration(audio_bytes)
                if measured_seconds is not None:
                    new_duration = datetime.timedelta(seconds=measured_seconds)
                    # Check if duration needs an update (ignore microsecond level noise if any, round to nearest float/int)
                    if step.duration != new_duration:
                        step.duration = new_duration
                        step.save(update_fields=['duration'])
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Updated step {step.pk} ({step.step_type}) to duration: {new_duration}"))
                    else:
                        skipped_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Could not parse duration for step {step.pk} ({step.step_type})"))
                    error_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing step {step.pk}: {e}"))
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculation complete. Total: {total_steps}, Updated: {updated_count}, "
                f"Skipped: {skipped_count}, Errors/Unparsed: {error_count}"
            )
        )
