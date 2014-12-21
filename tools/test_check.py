#! /usr/bin/env python

"""
Unit and functional tests for markdown lesson template validator.

Some of these tests require looking for example files, which exist only on
the gh-pages branch.   Some tests may therefore fail on branch "core".
"""


import imp
import logging
import os
import unittest

check = imp.load_source("check",  # Import non-.py file
                        os.path.join(os.path.dirname(__file__), "check"))

# Make log messages visible to help audit test failures
check.start_logging(level=logging.DEBUG)

MARKDOWN_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir))


class BaseTemplateTest(unittest.TestCase):
    """Common methods for testing template validators"""
    SAMPLE_FILE = "" # Path to a file that should pass all tests
    VALIDATOR = check.MarkdownValidator

    def _create_validator(self, markdown):
        """Create validator object from markdown string; useful for failures"""
        return self.VALIDATOR(markdown=markdown)


class TestAstHelpers(BaseTemplateTest):
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, 'index.md')
    VALIDATOR = check.MarkdownValidator

    def test_link_text_extracted(self):
        """Verify that link text and destination are extracted correctly"""
        validator = self._create_validator("""[This is a link](discussion.html)""")
        links = validator.ast.find_external_links(validator.ast.children[0])

        dest, link_text = validator.ast.get_link_info(links[0])
        self.assertEqual(dest, "discussion.html")
        self.assertEqual(link_text, "This is a link")


class TestIndexPage(BaseTemplateTest):
    """Test the ability to correctly identify and validate specific sections
        of a markdown file"""
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "index.md")
    VALIDATOR = check.IndexPageValidator

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)

    def test_headers_missing_hrs(self):
        validator = self._create_validator("""Blank row

layout: lesson
title: Lesson Title
keywords: ["some", "key terms", "in a list"]

Another section that isn't an HR
""")

        self.assertFalse(validator._validate_doc_headers())

    def test_headers_missing_a_line(self):
        """One of the required headers is missing"""
        validator = self._create_validator("""---
layout: lesson
keywords: ["some", "key terms", "in a list"]
---""")
        self.assertFalse(validator._validate_doc_headers())

    # TESTS INVOLVING DOCUMENT HEADER SECTION
    def test_headers_fail_with_other_content(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
keywords: ["some", "key terms", "in a list"]
otherline: Nothing
---""")
        self.assertFalse(validator._validate_doc_headers())

    def test_headers_fail_because_invalid_content(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
keywords: this is not a list
---""")
        self.assertFalse(validator._validate_doc_headers())

    # TESTS INVOLVING SECTION TITLES/HEADINGS
    def test_index_has_valid_section_headings(self):
        """The provided index page"""
        validator = self._create_validator("""## Topics

1.  [Topic Title One](01-one.html)
2.  [Topic Title Two](02-two.html)

## Other Resources

*   [Motivation](motivation.html)
*   [Reference Guide](reference.html)
*   [Next Steps](discussion.html)
*   [Instructor's Guide](instructors.html)""")
        res = validator._validate_section_heading_order()
        self.assertTrue(res)

    def test_index_fail_when_section_heading_absent(self):
        validator = self._create_validator("""## Topics

1.  [Topic Title One](01-one.html)
2.  [Topic Title Two](02-two.html)

## Other Resources

*   [Motivation](motivation.html)
*   [Reference Guide](reference.html)
*   [Next Steps](discussion.html)
*   [Instructor's Guide](instructors.html)""")
        res = validator.ast.has_section_heading("Fake heading")
        self.assertFalse(res)

    def test_fail_when_section_heading_is_wrong_level(self):
        """All headings must be exactly level 2"""
        validator = self._create_validator("""---
layout: page
title: Lesson Title
---
Paragraph of introductory material.

> ## Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.

### Topics

1.  [Topic Title 1](01-one.html)
2.  [Topic Title 2](02-two.html)

## Other Resources

*   [Motivation](motivation.html)
*   [Reference Guide](reference.html)
*   [Next Steps](discussion.html)
*   [Instructor's Guide](instructors.html)""")
        self.assertFalse(validator._validate_section_heading_order())

    def test_fail_when_section_headings_in_wrong_order(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
keywords: ["some", "key terms", "in a list"]
---
Paragraph of introductory material.

> ## Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.

## Other Resources

* [Motivation](motivation.html)
* [Reference Guide](reference.html)
* [Instructor's Guide](instructors.html)


## Topics

* [Topic Title 1](01-one.html)
* [Topic Title 2](02-two.html)""")

        self.assertFalse(validator._validate_section_heading_order())

    def test_pass_when_prereq_section_has_correct_heading_level(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
keywords: ["some", "key terms", "in a list"]
---
Paragraph of introductory material.

> ## Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.
""")
        self.assertTrue(validator._validate_intro_section())

    def test_fail_when_prereq_section_has_incorrect_heading_level(self):
        validator = self._create_validator("""---
layout: lesson
title: Lesson Title
keywords: ["some", "key terms", "in a list"]
---
Paragraph of introductory material.

> # Prerequisites
>
> A short paragraph describing what learners need to know
> before tackling this lesson.
""")
        self.assertFalse(validator._validate_intro_section())

    # TESTS INVOLVING LINKS TO OTHER CONTENT
    def test_file_links_validate(self):
        """Verify that all links in a sample file validate.
        Involves checking for example files; may fail on "core" branch"""
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator._validate_links()
        self.assertTrue(res)

    def test_html_link_to_extant_md_file_passes(self):
        """Verify that an HTML link with corresponding MD file will pass
        Involves checking for example files; may fail on "core" branch"""
        validator = self._create_validator("""[Topic Title One](01-one.html)""")
        self.assertTrue(validator._validate_links())

    def test_html_link_with_anchor_to_extant_md_passes(self):
        """Verify that link is identified correctly even if to page anchor

        For now this just tests that the regex handles #anchors.
         It doesn't validate that the named anchor exists in the md file

        Involves checking for example files; may fail on "core" branch
        """
        validator = self._create_validator("""[Topic Title One](01-one.html#anchor)""")
        self.assertTrue(validator._validate_links())

    def test_inpage_anchor_passes_validation(self):
        """Links that reference anchors within the page should be ignored"""
        # TODO: Revisit once anchor rules are available
        validator = self._create_validator("""Most databases also support Booleans and date/time values;
SQLite uses the integers 0 and 1 for the former, and represents the latter as discussed [earlier](#a:dates).""")
        self.assertTrue(validator._validate_links())

    def test_missing_markdown_file_fails_validation(self):
        """Fail validation when an html file is linked without corresponding
            markdown file"""
        validator = self._create_validator("""[Broken link](nonexistent.html)""")
        self.assertFalse(validator._validate_links())

    def test_website_link_ignored_by_validator(self):
        """Don't look for markdown if the file linked isn't local-
            remote website links are ignored"""
        validator = self._create_validator("""[Broken link](http://website.com/filename.html)""")
        self.assertTrue(validator._validate_links())

    def test_malformed_website_link_fails_validator(self):
        """If the link isn't prefixed by http(s):// or ftp://, fail.
         This is because there are a lot of edge cases in distinguishing
            between filenames and URLs: err on the side of certainty."""
        validator = self._create_validator("""[Broken link](www.website.com/filename.html)""")
        self.assertFalse(validator._validate_links())

    def test_finds_image_asset(self):
        """Image asset is found in the expected file location
        Involves checking for example files; may fail on "core" branch"""
        validator = self._create_validator(
            """![this is the image's title](fig/example.svg "this is the image's alt text")""")
        self.assertTrue(validator._validate_links())

    def test_image_asset_not_found(self):
        """Image asset can't be found if path is invalid"""
        validator = self._create_validator(
            """![this is the image's title](fig/exemple.svg "this is the image's alt text")""")
        self.assertFalse(validator._validate_links())

    def test_non_html_link_finds_csv(self):
        """Look for CSV file in appropriate folder
        Involves checking for example files; may fail on "core" branch
        """
        validator = self._create_validator(
            """Use [this CSV](data/data.csv) for the exercise.""")
        self.assertTrue(validator._validate_links())

    def test_non_html_links_are_path_sensitive(self):
        """Fails to find CSV file with wrong path."""
        validator = self._create_validator(
            """Use [this CSV](data.csv) for the exercise.""")
        self.assertFalse(validator._validate_links())


class TestTopicPage(BaseTemplateTest):
    """Verifies that the topic page validator works as expected"""
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "01-one.md")
    VALIDATOR = check.TopicPageValidator

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)


class TestMotivationPage(BaseTemplateTest):
    """Verifies that the instructors page validator works as expected"""
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "motivation.md")
    VALIDATOR = check.MotivationPageValidator

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)


class TestReferencePage(BaseTemplateTest):
    """Verifies that the reference page validator works as expected"""
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "reference.md")
    VALIDATOR = check.ReferencePageValidator

    def test_missing_glossary_definition(self):
        validator = self._create_validator("")
        self.assertFalse(validator._validate_glossary_entry(
            ["Key word"]))

    def test_missing_colon_at_glossary_definition(self):
        validator = self._create_validator("")
        self.assertFalse(validator._validate_glossary_entry(
            ["Key word", "Definition of term"]))

    def test_wrong_indentation_at_glossary_definition(self):
        validator = self._create_validator("")
        self.assertFalse(validator._validate_glossary_entry(
            ["Key word", ": Definition of term"]))

    def test_wrong_continuation_at_glossary_definition(self):
        validator = self._create_validator("")
        self.assertFalse(validator._validate_glossary_entry(
            ["Key word", ":   Definition of term", "continuation"]))

    def test_valid_glossary_definition(self):
        validator = self._create_validator("")
        self.assertTrue(validator._validate_glossary_entry(
            ["Key word", ":   Definition of term", "    continuation"]))

    def test_only_definitions_can_appear_after_glossary_heading(self):
        validator = self._create_validator("""## Glossary

Key Word 1
:   Definition of first term

Paragraph

Key Word 2
:   Definition of second term
""")
        self.assertFalse(validator._validate_glossary())

    def test_glossary(self):
        validator = self._create_validator("""## Glossary

Key Word 1
:   Definition of first term

Key Word 2
:   Definition of second term
""")
        self.assertTrue(validator._validate_glossary())

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)


class TestInstructorPage(BaseTemplateTest):
    """Verifies that the instructors page validator works as expected"""
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "instructors.md")
    VALIDATOR = check.InstructorPageValidator

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)


class TestLicensePage(BaseTemplateTest):
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "LICENSE.md")
    VALIDATOR = check.LicensePageValidator

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)

    def test_modified_file_fails_validation(self):
        with open(self.SAMPLE_FILE, 'rU') as f:
            orig_text = f.read()
        mod_text = orig_text.replace("The", "the")
        validator = self._create_validator(mod_text)
        self.assertFalse(validator.validate())


class TestDiscussionPage(BaseTemplateTest):
    SAMPLE_FILE = os.path.join(MARKDOWN_DIR, "discussion.md")
    VALIDATOR = check.DiscussionPageValidator

    def test_sample_file_passes_validation(self):
        sample_validator = self.VALIDATOR(self.SAMPLE_FILE)
        res = sample_validator.validate()
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
