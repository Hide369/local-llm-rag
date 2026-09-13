---
name: markdown
repo: github/docs
ref: main
commit: 078b5832caa5cde591c2babb389ef447a0ef66eb
source_path: content/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections.md
title: Organizing information with collapsed sections
version: 0.0.0
fetched_at: 2026-09-13
---
## Creating a collapsed section

You can temporarily obscure sections of your Markdown by creating a collapsed section that the reader can choose to expand. For example, when you want to include technical details in an issue comment that may not be relevant or interesting to every reader, you can put those details in a collapsed section.

Any Markdown within the `<details>` block will be collapsed until the reader clicks  to expand the details.

Within the `<details>` block, use the `<summary>` tag to let readers know what is inside. The label appears to the right of .

````markdown
<details>

<summary>Tips for collapsed sections</summary>

### You can add a header

You can add text within a collapsed section.

You can add an image or a code block, too.

```ruby
   puts "Hello World"
```

</details>
````

The Markdown inside the `<summary>` label will be collapsed by default:

![Screenshot of the Markdown above on this page as rendered on , showing a right-facing arrow and the header "Tips for collapsed sections."](/assets/images/help/writing/collapsed-section-view.png)

After a reader clicks , the details are expanded:

![Screenshot of the Markdown above on this page as rendered on . The collapsed section contains headers, text, images, and code blocks.](/assets/images/help/writing/open-collapsed-section.png)

Optionally, to make the section display as open by default, add the `open` attribute to the `<details>` tag:

```html
<details open>
```

## Further reading

* [ Flavored Markdown Spec](https://github.github.com/gfm/)
* [AUTOTITLE](/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
