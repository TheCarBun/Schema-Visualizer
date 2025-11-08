# import json
from pydantic import BaseModel
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()


class DataTypeSchema(BaseModel):
    field: str
    datatype: str


class FieldSchema(BaseModel):
    field_name: str
    summary: str
    subfields: list[str]
    required_subfields: list[str]
    datatypes: list[DataTypeSchema]


class OutputSchema(BaseModel):
    schema_title: str
    fields: list[FieldSchema]


client = genai.Client()
models = ['gemini-2.0-flash-lite', 'gemini-2.0-flash',
          'gemini-2.5-flash-lite', 'gemini-2.5-flash']

instructions = """
You are a highly efficient data analyst specializing in converting complex technical schemas into simplified, structured JSON formats. Your task is to analyze the provided JSON Schema and return a single, valid JSON object.

Your JSON output MUST adhere to the following strict structure:

1.  The root of the JSON object must have two properties: `schema_title` and `fields`.

2.  **`schema_title`**: A string. Find `title` of schema or Generate a concise, human-readable title for the entire schema. Base this on the schema's overall purpose or root `description`. If a description is not available, create a generic but fitting title (e.g., "User Profile Schema").

3.  **`fields`**: An array of objects. This array must contain one object for each top-level key defined in the input schema's root `properties`.

4.  Each object within the `fields` array must have the following properties:
    * **`field_name`**: A string. The name of the top-level field (the key).
    * **`summary`**: A string. A short, one-to-two-sentence summary describing the purpose and content of this specific top-level field.
    * **`subfields`**: An array of strings. List the names of all sub-fields within this top-level field.
    * **`required_subfields`**: An array of strings. List the names of all sub-fields that are designated as 'required' within this top-level field's properties. If there are no required sub-fields, return an empty array `[]`.
    * **`datatypes`**: An list of objects mapping each subfield name to its data type. Available datatypes str, int, obj, float, list, bool, other.

**IMPORTANT:** The final response must be only the raw JSON object. Do not include any introductory or concluding text, explanations, or Markdown formatting. The response must start with `{` and end with `}`.

**Example Input Schema:**
```json
{
  "title": "User API Schema",
  "type": "object",
  "properties": {
    "user_info": {
      "type": "object",
      "description": "General information about the user.",
      "properties": {
        "user_id": { "type": "string" },
        "email": { "type": "string" }
      },
      "required": ["user_id", "email"]
    },
    "preferences": {
      "type": "object",
      "description": "User's settings and preferences.",
      "properties": {
        "theme": { "type": "string", "default": "light" },
        "notifications": { "type": "boolean" }
      }
    }
  }
}
```

Example Output:
```json
{
  "schema_title": "User API Schema",
  "fields": [
    {
      "field_name": "user_info",
      "summary": "This object contains essential user details, including unique identifiers and contact information.",
      "subfields": ["user_id", "email"],
      "required_subfields": ["user_id", "email"],
      "datatypes": [
        {
          "field": "user_id",
          "datatype": "str"
        },
        {
          "field": "email",
          "datatype": "str"
        }
      ]
    },
    {
      "field_name": "preferences",
      "summary": "This object holds various user settings, such as theme and notification options.",
      "subfields": ["theme", "notifications"],
      "required_subfields": [],
      "datatypes": [
        {
          "field": "theme",
          "datatype": "str"
        },
        {
          "field": "notifications",
          "datatype": "bool"
        }
      ]
    }
  ]
}
```
"""

st.set_page_config(
    page_title="Schema Helper",
    page_icon="🗒️",
    initial_sidebar_state="expanded"
)

with st.sidebar:

    # Define datatype color mapping
    datatype_colors = {
        "str": "green",
        "obj": "red",
        "int": "blue",
        "float": "orange",
        "list": "yellow",
        "bool": "violet",
        "null": "gray"
    }

    with st.container(border=True):
        legend_items = []
        for dtype, color in datatype_colors.items():
            legend_items.append(f":{color}-badge[{dtype}]")
        st.markdown(" ".join(legend_items) +
                    ":grey-badge[:material/radio_button_unchecked: Optional]  :grey-badge[:material/radio_button_checked: Required]")

    with st.container(border=True):
        st.write("Pick a model")
        model_name = st.radio(label="model_name", options=models,
                              index=3, label_visibility="collapsed")
    schema = st.text_area(
        label="Schema:", placeholder="Paste your schema here")


if len(schema) > 100:
    anl_button = st.sidebar.button("Analyze")
    if anl_button:
        with st.spinner(text="Analyzing Schema...", show_time=True):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_text(text=schema),
                        instructions
                    ],
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": OutputSchema
                    }
                )

            # with open('response.json', 'w', encoding='utf-8') as f:
            #     json.dump(response.model_dump_json(indent=2),
            #               f, ensure_ascii=False, indent=2)

                response_txt = response.text
                if response_txt.startswith("```json"):
                    st.json(response.text)
                else:
                    response_json: OutputSchema = response.parsed

                    st.markdown(f"## {response_json.schema_title}")

                    fields = response_json.fields
                    for i, field in enumerate(fields):
                        with st.container(border=True, key=i):

                            # Generate badges for each subfield
                            badges_txt = ""
                            for sub in field.subfields:
                                # Find datatype from datatypes list
                                datatype = next(
                                    (dt.datatype for dt in field.datatypes if dt.field == sub), "unknown")
                                is_required = sub in field.required_subfields
                                color = datatype_colors.get(
                                    datatype, "grey")
                                icon = ":material/radio_button_checked:" if is_required else ":material/radio_button_unchecked:"
                                badges_txt += f":{color}-badge[{icon} {sub}] "

                            # --- Display ---
                            # Field name, required count and summary
                            col1, col2 = st.columns(
                                [3, 1], vertical_alignment="center")
                            col1.markdown(f'### `{field.field_name}`')
                            with col2:
                                # Show required fields count
                                required_count = len(field.required_subfields)
                                total_count = len(field.subfields)
                                st.caption(
                                    f"Required: {required_count}/{total_count}")

                            st.write(field.summary)
                            st.markdown(badges_txt)

            except Exception as e:
                st.error(f"Error: {e}")
