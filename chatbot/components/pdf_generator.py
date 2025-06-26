"""
PDF report generation component for college recommendations.
Optimized for low-resource environments (2GB RAM, 1 vCPU).
"""

import asyncio
import gc
import io
import re
from datetime import datetime
from typing import Any

import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from chatbot.workflow.state import GraphState
from projectutils.logger import setup_logger

logger = setup_logger(__file__)


def _get_top_5_ranked_college_report_data(messages: list[dict]) -> list[dict]:
    """
    Extract top 5 ranked college data from messages with college_ranking metadata.

    Args:
        messages: List of message dictionaries from state

    Returns:
        List of dictionaries with college data, sorted by rank (Rank 1 first)
        Each dict contains: {'name': str, 'rank': int, 'source_path': str}
    """
    college_data = []

    for message in messages:
        metadata = message.get("metadata", {})
        if metadata.get("message_type") == "college_ranking":
            content = message.get("content", "")
            college_name = metadata.get("college_name", "Unknown College")
            source_path = metadata.get("source_path")

            # Extract rank from content (format: "### Rank X: College Name")
            rank = None
            lines = content.strip().split("\n")
            if lines:
                rank_line = lines[0].replace("### ", "")
                rank_match = re.search(r"Rank (\d+):", rank_line)
                if rank_match:
                    rank = int(rank_match.group(1))

            if rank is not None and source_path:
                college_data.append(
                    {"name": college_name, "rank": rank, "source_path": source_path}
                )

    # Sort by rank and return top 5
    college_data.sort(key=lambda x: x["rank"])
    return college_data[:5]


def _convert_markdown_to_reportlab_elements(
    markdown_text: str, styles_dict: dict
) -> list:
    """
    Convert markdown text to ReportLab flowable elements.

    Args:
        markdown_text: The markdown content to convert
        styles_dict: Dictionary containing ReportLab ParagraphStyle objects
                    (h1_style, h2_style, h3_style, body_style, bold_body_style)

    Returns:
        List of ReportLab Flowable objects (Paragraph, Spacer, etc.)
    """
    elements = []
    lines = markdown_text.strip().split("\n")  # Strip the entire text first

    consecutive_empty_lines = 0

    for _i, line in enumerate(lines):
        line = line.strip()

        if not line:
            consecutive_empty_lines += 1
            # Only add spacer for the first empty line in a sequence, and limit to reasonable spacing
            if consecutive_empty_lines == 1:
                elements.append(Spacer(1, 0.15 * inch))  # Reduced spacing
            continue
        else:
            consecutive_empty_lines = 0  # Reset counter when non-empty line is hit

        # Skip horizontal rules
        if line == "---" or line.startswith("---"):
            # Add a small spacer instead of showing the dashes
            elements.append(Spacer(1, 0.1 * inch))
            continue

        if line.startswith("#### "):
            # H4 heading - use smaller bold style
            text = line[5:].strip()
            # Handle backticks in headings
            text = re.sub(r"`([^`]+)`", r"\1", text)
            elements.append(Paragraph(f"<b>{text}</b>", styles_dict["body_style"]))

        elif line.startswith("### "):
            # H3 heading - use dedicated h3 style if available, otherwise bold h2
            text = line[4:].strip()
            # Handle backticks in headings
            text = re.sub(r"`([^`]+)`", r"\1", text)
            h3_style = styles_dict.get("h3_style", styles_dict["h2_style"])
            elements.append(Paragraph(f"<b>{text}</b>", h3_style))

        elif line.startswith("## "):
            # H2 heading
            text = line[3:].strip()
            # Handle backticks in headings
            text = re.sub(r"`([^`]+)`", r"\1", text)
            elements.append(Paragraph(text, styles_dict["h2_style"]))

        elif line.startswith("# "):
            # H1 heading
            text = line[2:].strip()
            # Handle backticks in headings
            text = re.sub(r"`([^`]+)`", r"\1", text)
            elements.append(Paragraph(text, styles_dict["h1_style"]))

        elif line.startswith("- ") or line.startswith("* "):
            # List item
            item_text = line[2:].strip()
            # Apply bold and italic formatting
            item_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", item_text)
            item_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", item_text)
            # Handle backticks for code spans
            item_text = re.sub(r"`([^`]+)`", r"\1", item_text)
            elements.append(Paragraph(f"• {item_text}", styles_dict["body_style"]))

        else:
            # Regular body text
            # Apply bold and italic formatting
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
            text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
            # Handle backticks for code spans - remove backticks and keep the content plain
            text = re.sub(r"`([^`]+)`", r"\1", text)
            elements.append(Paragraph(text, styles_dict["body_style"]))

    # Remove trailing spacers to prevent blank pages
    while elements and isinstance(elements[-1], Spacer):
        elements.pop()

    return elements


async def generate_pdf_report(state: GraphState) -> dict[str, Any] | None:
    """Generate a PDF report with college recommendations using ReportLab."""
    try:
        logger.info("Starting PDF report generation")

        # Yield control to allow UI updates
        await asyncio.sleep(0.1)

        # Create a BytesIO buffer to store the PDF
        buffer = io.BytesIO()

        # Define consistent style palette
        base_font_name = "Helvetica"
        bold_font_name = "Helvetica-Bold"
        primary_color = colors.HexColor("#003366")  # dark blue
        secondary_color = colors.HexColor("#4A90E2")  # medium blue
        text_color = colors.HexColor("#333333")  # dark grey
        light_gray_color = colors.HexColor("#E0E0E0")  # for borders/backgrounds
        background_color_odd_row = colors.HexColor("#F7F9FC")
        background_color_even_row = colors.white

        # Get styles
        styles = getSampleStyleSheet()

        # Define new paragraph styles
        document_title_style = ParagraphStyle(
            "DocumentTitle",
            parent=styles["Title"],
            fontName=bold_font_name,
            fontSize=22,
            spaceAfter=16,
            alignment=1,  # Center
            textColor=primary_color,
        )

        generated_on_style = ParagraphStyle(
            "GeneratedOn",
            parent=styles["Normal"],
            fontName=base_font_name,
            fontSize=9,
            alignment=1,  # Center
            textColor=text_color,
            spaceAfter=24,
        )

        h1_style = ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontName=bold_font_name,
            fontSize=16,
            spaceBefore=18,
            spaceAfter=10,
            textColor=primary_color,
            leading=20,
        )

        h2_style = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontName=bold_font_name,
            fontSize=13,  # Smaller than H1
            spaceBefore=14,
            spaceAfter=8,
            textColor=secondary_color,  # Different color for hierarchy
            leading=18,
        )

        # Add H3 style for proper ### heading support
        h3_style = ParagraphStyle(
            "H3",
            parent=styles["Heading3"],
            fontName=bold_font_name,
            fontSize=11,  # Smaller than H2
            spaceBefore=10,
            spaceAfter=6,
            textColor=text_color,  # Use text color for lower level headings
            leading=16,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName=base_font_name,
            fontSize=10,
            textColor=text_color,
            leading=14,  # Line spacing
            spaceAfter=6,
        )

        bold_body_style = ParagraphStyle(
            "BoldBody",
            parent=body_style,
            fontName=bold_font_name,
        )

        # Create styles dictionary for markdown conversion
        styles_dict = {
            "h1_style": h1_style,
            "h2_style": h2_style,
            "h3_style": h3_style,
            "body_style": body_style,
            "bold_body_style": bold_body_style,
        }

        # Footer canvas function for page numbers
        def footer_canvas(canvas, doc):
            canvas.saveState()
            footer_style = ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontName=base_font_name,
                fontSize=9,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
            p = Paragraph(f"Page {doc.page}", footer_style)
            w, h = p.wrapOn(canvas, doc.width, doc.bottomMargin)
            p.drawOn(canvas, doc.leftMargin, h)  # Draw at bottom margin height
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,  # Ensure enough bottom margin for footer
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )

        story = []

        # Get messages first - needed for various extractions
        messages = state.get("messages", [])

        # Add title with new styles
        story.append(Paragraph("College Recommendation Report", document_title_style))
        story.append(
            Paragraph(
                f"Generated on {datetime.now().strftime('%B %d, %Y')}",
                generated_on_style,
            )
        )

        # Yield control after basic setup
        await asyncio.sleep(0.1)

        # Add SAT Profile with improved formatting
        current_sat_profile = state.get("current_sat_profile", {})
        if current_sat_profile:
            story.append(Paragraph("Your SAT Profile", h1_style))
            sat_score = current_sat_profile.get("score", "N/A")
            sat_source = current_sat_profile.get("source_type", "N/A").title()
            sat_range = f"{current_sat_profile.get('lower_bound', 'N/A')}-{current_sat_profile.get('upper_bound', 'N/A')}"

            # Create SAT data as a table for better alignment
            sat_data_table = [
                [
                    Paragraph("<b>Score:</b>", body_style),
                    Paragraph(str(sat_score), body_style),
                ],
                [
                    Paragraph("<b>Estimated Range:</b>", body_style),
                    Paragraph(str(sat_range), body_style),
                ],
                [
                    Paragraph("<b>Source:</b>", body_style),
                    Paragraph(str(sat_source), body_style),
                ],
            ]
            sat_table = Table(sat_data_table, colWidths=[1.5 * inch, 4.5 * inch])
            sat_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(sat_table)
            story.append(Spacer(1, 12))  # Reduced spacer

        # Add comparison table
        comparison_table_content = _extract_comparison_table(messages)
        if comparison_table_content:
            story.append(Paragraph("Your Shortlisted Colleges: At a Glance", h1_style))
            table = _convert_markdown_table_to_reportlab(
                comparison_table_content,
                primary_color,
                secondary_color,
                text_color,
                light_gray_color,
                background_color_odd_row,
                background_color_even_row,
                base_font_name,
                bold_font_name,
            )
            if table:
                story.append(table)
                story.append(Spacer(1, 18))

        # Yield control after table processing
        await asyncio.sleep(0.1)

        # Add plots with KeepTogether to prevent splitting
        plots = _extract_plots_from_messages(messages)
        if plots:
            logger.info(f"Converting {len(plots)} charts to images...")

        for plot_title, fig in plots:
            # Create Paragraph for title
            title_para = Paragraph(plot_title, h1_style)

            try:
                # OPTIMIZED: Smaller dimensions + JPEG format for faster processing
                # Reduces processing time and memory usage for low-resource environments
                img_bytes = pio.to_image(
                    fig,
                    format="jpeg",  # Faster than PNG
                    width=600,  # Reduced from 1200 (50% smaller)
                    height=400,  # Reduced from 800 (50% smaller)
                    engine="kaleido",  # Kaleido v1 handles process management automatically
                    scale=1,  # Prevent auto-scaling that uses more memory
                )

                img_buffer = io.BytesIO(img_bytes)
                img = Image(
                    img_buffer, width=5.5 * inch, height=3.5 * inch
                )  # Smaller PDF size

                # Group title, a small spacer, and image to keep them together
                plot_group = KeepTogether([title_para, Spacer(1, 0.1 * inch), img])
                story.append(plot_group)
                story.append(Spacer(1, 12))  # Reduced spacing

                logger.info(f"Successfully converted plot: {plot_title}")

                # Force garbage collection after heavy chart processing to free memory
                gc.collect()

                # Yield control after each plot to prevent blocking
                await asyncio.sleep(0.2)

            except Exception as e:
                logger.warning(f"Failed to convert plot '{plot_title}' to image: {e}")
                # Add title and text summary instead of the plot
                story.append(title_para)
                story.append(
                    Paragraph(
                        f"Chart visualization unavailable due to resource constraints. Data summary: {plot_title}",
                        body_style,
                    )
                )
                story.append(Spacer(1, 12))

                # Clean up any partial resources
                gc.collect()

        # Add college rankings with improved styling
        final_docs = state.get("final_docs", {})
        wants_clarification = state.get("wants_clarification")
        has_reranked_docs = (
            any(doc.metadata.get("llm_rank") is not None for doc in final_docs.values())
            if final_docs
            else False
        )

        if wants_clarification is True and has_reranked_docs:
            story.append(PageBreak())  # Start on a new page
            story.append(Paragraph("Top College Recommendations", h1_style))

            top_5_content = _extract_top_5_college_details(messages)
            for college_content in top_5_content:
                # Extract rank and college name
                lines = college_content.strip().split("\n")
                rank_line = lines[0].replace("### ", "") if lines else ""

                # Create improved college card style
                college_card_para_style = ParagraphStyle(
                    "CollegeCardPara",
                    parent=body_style,
                    fontSize=10,
                    leading=13,
                    spaceAfter=10,  # Space after the card
                    leftIndent=0,  # No indent for the paragraph itself, border provides visual indent
                    rightIndent=0,
                    borderColor=primary_color,
                    borderWidth=1,
                    borderPadding=10,  # Padding inside the border
                )

                if rank_line:
                    story.append(Paragraph(rank_line, h2_style))

                # Add reasoning
                reasoning = "\n".join(lines[1:]).replace("**Reasoning:**", "").strip()
                if reasoning:
                    story.append(Paragraph(reasoning, college_card_para_style))

                story.append(Spacer(1, 12))

            # Yield control after rankings
            await asyncio.sleep(0.1)

            # Add detailed college reports section
            college_report_data = _get_top_5_ranked_college_report_data(messages)
            if college_report_data:
                # Start detailed reports on a new page if there's prior content
                if len(story) > 3:  # More than just title and basic header info
                    story.append(PageBreak())

                story.append(Paragraph("Detailed College Reports", h1_style))
                story.append(Spacer(1, 12))

                for i, college_info in enumerate(college_report_data):
                    college_name = college_info["name"]
                    rank = college_info["rank"]
                    source_path = college_info["source_path"]

                    # Add page break before each college report (except the first one)
                    if i > 0:  # Not the first college
                        story.append(PageBreak())

                    try:
                        # Read the markdown file content
                        with open(source_path, encoding="utf-8") as f:
                            markdown_content = f.read()

                        # Add college header
                        story.append(
                            Paragraph(f"Rank {rank}: {college_name}", h1_style)
                        )
                        story.append(Spacer(1, 8))

                        # Convert markdown to ReportLab elements
                        college_elements = _convert_markdown_to_reportlab_elements(
                            markdown_content, styles_dict
                        )

                        # Add all elements for this college
                        story.extend(college_elements)

                        # Yield control after each college report
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Failed to read markdown file {source_path}: {e}")
                        # Add error message for this college
                        story.append(
                            Paragraph(f"Rank {rank}: {college_name}", h1_style)
                        )
                        story.append(
                            Paragraph(
                                f"Error loading college details: {str(e)}", body_style
                            )
                        )
                        story.append(Spacer(1, 12))

        # Remove any trailing spacers to prevent blank pages
        while story and isinstance(story[-1], Spacer):
            story.pop()

        # Yield control before final PDF build
        await asyncio.sleep(0.1)

        # Build PDF with page numbers
        doc.build(story, onLaterPages=footer_canvas, onFirstPage=footer_canvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"college_recommendation_report_{timestamp}.pdf"

        logger.info(f"PDF report generated successfully: {filename}")
        return {"filename": filename, "content": pdf_bytes, "mime": "application/pdf"}

    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)

        return None


def _extract_comparison_table(messages: list[dict]) -> str | None:
    """Extract the comparison table markdown from messages."""
    for message in messages:
        content = message.get("content", "")
        if content.startswith("## 🎓 Your Shortlisted Colleges: At a Glance"):
            return content
    return None


def _extract_plots_from_messages(messages: list[dict]) -> list[tuple[str, Any]]:
    """Extract Plotly figures from messages and return them with titles."""
    plots = []

    for message in messages:
        content = message.get("content", "")
        elements = message.get("elements", [])

        # Look for plots by their content identifiers
        if "## 💰 Show Me the Money!" in content:
            for element in elements:
                if hasattr(element, "figure"):
                    plots.append(("Show Me the Money!", element.figure))
                    break
        elif "## 🎯 What Are My Odds?" in content:
            for element in elements:
                if hasattr(element, "figure"):
                    plots.append(("What Are My Odds?", element.figure))
                    break

    return plots


def _convert_markdown_table_to_reportlab(
    markdown_content: str,
    primary_color,
    secondary_color,
    text_color,
    light_gray_color,
    background_color_odd_row,
    background_color_even_row,
    base_font_name,
    bold_font_name,
) -> Table | None:
    """Convert markdown table to ReportLab Table with enhanced styling."""
    try:
        # Get styles for paragraphs
        styles = getSampleStyleSheet()

        # Define paragraph styles for table cells
        cell_style = ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName=base_font_name,
            fontSize=8,
            textColor=text_color,
            leading=10,
            alignment=TA_LEFT,
        )
        cell_style_right = ParagraphStyle(
            name="TableCellRight", parent=cell_style, alignment=TA_RIGHT
        )
        link_cell_style = ParagraphStyle(
            name="LinkTableCell",
            parent=cell_style,
            textColor=colors.blue,
        )
        header_cell_style = ParagraphStyle(
            name="HeaderTableCell",
            parent=styles["Normal"],
            fontName=bold_font_name,
            fontSize=9,
            textColor=colors.white,
            leading=11,
            alignment=TA_LEFT,
            wordWrap="LTR",  # Enable word wrapping
        )

        # Extract table from markdown content
        lines = markdown_content.split("\n")
        table_lines = []
        in_table = False

        for line in lines:
            if "|" in line and not line.strip().startswith("|------"):
                in_table = True
                # Clean up the line and split by |
                clean_line = line.strip()
                if clean_line.startswith("|"):
                    clean_line = clean_line[1:]
                if clean_line.endswith("|"):
                    clean_line = clean_line[:-1]

                cells = [cell.strip() for cell in clean_line.split("|")]
                table_lines.append(cells)
            elif in_table and "|" not in line:
                break

        if not table_lines:
            return None

        # Process cells into Paragraphs with link support
        data = []
        for i, row_cells in enumerate(table_lines):
            processed_row = []
            for j, cell_text in enumerate(row_cells):
                # Determine cell style based on position
                if i == 0:  # Header row
                    current_cell_style = header_cell_style
                elif j >= 2:  # Numeric columns (tuition, rates, etc.) - right aligned
                    current_cell_style = cell_style_right
                else:  # Text columns (college name, location) - left aligned
                    current_cell_style = cell_style

                # Check for markdown link in body cells (first column usually has links)
                if i > 0 and j == 0:  # Check only first column body cells for links
                    match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", cell_text)
                    if match:
                        link_text, url_part = match.groups()
                        # Ensure URL is complete
                        if (
                            not url_part.startswith(("http://", "https://"))
                            and url_part
                        ):
                            url_part = "http://" + url_part
                        processed_row.append(
                            Paragraph(
                                f'<a href="{url_part}"><u>{link_text}</u></a>',
                                link_cell_style,
                            )
                        )
                        continue

                # Default processing for non-link cells or header cells
                # Shorten and add line breaks to specific headers for better PDF rendering
                if i == 0:  # Header row
                    if cell_text == "Acceptance Rate":
                        cell_text = "Accept<br/>Rate"
                    elif cell_text == "Avg Aid":
                        cell_text = "Avg<br/>Aid"
                    elif cell_text == "Student-Faculty Ratio":
                        cell_text = "Student<br/>Faculty<br/>Ratio"
                    elif cell_text == "Admission Category":
                        cell_text = "Admit<br/>Category"
                    elif cell_text == "Tuition (Private)":
                        cell_text = "Tuition<br/>(Private)"
                    elif cell_text == "Tuition (In-State)":
                        cell_text = "Tuition<br/>(In-State)"
                    elif cell_text == "Tuition (Out-of-State)":
                        cell_text = "Tuition<br/>(Out-State)"

                processed_row.append(Paragraph(cell_text, current_cell_style))
            data.append(processed_row)

        # Dynamically calculate column widths
        header_cells = table_lines[0]
        num_cols = len(header_cells)

        available_width = letter[0] - (0.75 * inch * 2)  # Page width - margins

        # Define column weight system for flexible allocation
        col_weights = []

        # Create a mapping of column types to their weights
        for header in header_cells:
            if header == "College":
                col_weights.append(3.5)  # Wider for college names
            elif header == "Location":
                col_weights.append(2.5)  # Medium for location
            elif header in [
                "Tuition (In-State)",
                "Tuition (Out-of-State)",
                "Tuition (Private)",
            ]:
                col_weights.append(2.0)  # Medium for tuition columns
            elif header == "Acceptance Rate":
                col_weights.append(1.5)  # Narrower for percentages
            elif header == "Avg Aid":
                col_weights.append(1.5)  # Narrower for aid amounts
            elif header == "Student-Faculty Ratio":
                col_weights.append(1.8)  # Slightly wider for ratios
            elif header == "Admission Category":
                col_weights.append(2.2)  # Medium-wide for categories
            else:
                col_weights.append(1.5)  # Default weight for unknown columns

        # Calculate proportional widths based on weights
        total_weight = sum(col_weights)
        col_widths = [
            (weight / total_weight) * available_width for weight in col_weights
        ]

        # Apply minimum width constraints to prevent columns from being too narrow
        min_width = 0.6 * inch
        adjusted_widths = []
        total_min_adjustment = 0

        for width in col_widths:
            if width < min_width:
                adjusted_widths.append(min_width)
                total_min_adjustment += min_width - width
            else:
                adjusted_widths.append(width)

        # If minimum widths were applied, redistribute the excess from wider columns
        if total_min_adjustment > 0:
            # Find columns that can be reduced (those above minimum)
            reducible_indices = [
                i for i, w in enumerate(adjusted_widths) if w > min_width
            ]

            if reducible_indices:
                reduction_per_col = total_min_adjustment / len(reducible_indices)
                for i in reducible_indices:
                    # Reduce width but not below minimum
                    new_width = max(min_width, adjusted_widths[i] - reduction_per_col)
                    adjusted_widths[i] = new_width

        col_widths = adjusted_widths

        # Final safety check: if total width exceeds available, scale everything down
        total_width = sum(col_widths)
        if total_width > available_width:
            logger.warning(
                f"Calculated column widths ({total_width:.2f}) exceed available width ({available_width:.2f}). Scaling down proportionally."
            )
            scale_factor = available_width / total_width
            col_widths = [w * scale_factor for w in col_widths]

        # Ensure col_widths has the correct number of elements
        if len(col_widths) != num_cols:
            logger.error(
                f"Mismatch in calculated column widths. Expected {num_cols}, got {len(col_widths)}. Defaulting widths."
            )
            # Fallback to equal widths if calculation fails
            col_widths = [available_width / num_cols] * num_cols

        # Create ReportLab Table with calculated column widths
        table = Table(data, colWidths=col_widths)

        # Apply enhanced table styling
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),  # Header background
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            # Alternating row colors
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [background_color_odd_row, background_color_even_row],
            ),
            ("GRID", (0, 0), (-1, -1), 0.5, light_gray_color),  # Lighter grid
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            (
                "TOPPADDING",
                (0, 1),
                (-1, -1),
                5,
            ),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]

        table.setStyle(TableStyle(style_commands))

        return table

    except Exception as e:
        logger.error(f"Error converting markdown table to PDF: {e}")
        return None


def _extract_top_5_college_details(messages: list[dict]) -> list[str]:
    """Extract Top 5 college ranking cards from messages with college_ranking metadata."""
    college_details = []

    for message in messages:
        metadata = message.get("metadata", {})
        if metadata.get("message_type") == "college_ranking":
            content = message.get("content", "")

            # Clean up the content for PDF display
            # Remove markdown links and buttons, keep the core ranking information
            content = re.sub(
                r"\[([^\]]+)\]\([^\)]+\)", r"\1", content
            )  # Remove markdown links
            content = re.sub(
                r"🌐 \*\*Click college name above to view official page\*\*\n?",
                "",
                content,
            )
            content = re.sub(r"📄 \*\*Click to View:\*\* [^\n]+\n?", "", content)

            # Clean up extra whitespace
            content = re.sub(r"\n\s*\n", "\n\n", content.strip())

            college_details.append(content)

    return college_details[:5]  # Return only top 5
