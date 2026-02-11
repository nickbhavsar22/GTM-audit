"""PDF export using Weasyprint."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFExporter:
    """Convert HTML report to PDF using Weasyprint."""

    def export(self, html_content: str, output_path: str | Path) -> str:
        """Generate PDF from HTML content.

        Args:
            html_content: Full HTML report string.
            output_path: Where to save the PDF file.

        Returns:
            The output file path as a string.
        """
        output_path = str(output_path)

        try:
            from weasyprint import HTML

            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"PDF generated: {output_path}")
            return output_path
        except ImportError:
            logger.warning(
                "Weasyprint not installed. Install with: pip install weasyprint"
            )
            raise ImportError(
                "Weasyprint is required for PDF export. "
                "Install with: pip install weasyprint"
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise
