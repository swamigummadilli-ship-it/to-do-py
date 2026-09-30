from datetime import datetime
from typing import Any

import streamlit as st


def init_state() -> None:
    """Initialize the per-browser-session task state."""
    defaults: dict[str, Any] = {
        "tasks": [],
        "next_id": 1,
        "editing_id": None,
        "confirm_delete_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_task(title: str, description: str) -> bool:
    """Add a task, returning False when its title is blank."""
    init_state()
    clean_title = title.strip()
    if not clean_title:
        return False

    task_id = st.session_state.next_id
    st.session_state.tasks.append(
        {
            "id": task_id,
            "title": clean_title,
            "description": description.strip(),
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )
    st.session_state.next_id += 1
    return True


def toggle_task(task_id: int) -> bool:
    """Toggle a task's completion state; return False if it no longer exists."""
    init_state()
    for task in st.session_state.tasks:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]
            return True
    return False


def update_task(task_id: int, title: str, description: str) -> bool:
    """Update an existing task, rejecting blank titles and missing IDs."""
    init_state()
    clean_title = title.strip()
    if not clean_title:
        return False

    for task in st.session_state.tasks:
        if task["id"] == task_id:
            task["title"] = clean_title
            task["description"] = description.strip()
            return True
    return False


def delete_task(task_id: int) -> bool:
    """Delete a task and clear any UI state referring to it."""
    init_state()
    original_count = len(st.session_state.tasks)
    st.session_state.tasks = [
        task for task in st.session_state.tasks if task["id"] != task_id
    ]
    if len(st.session_state.tasks) == original_count:
        return False

    if st.session_state.editing_id == task_id:
        st.session_state.editing_id = None
    if st.session_state.confirm_delete_id == task_id:
        st.session_state.confirm_delete_id = None
    st.session_state.pop(f"edit_title_{task_id}", None)
    st.session_state.pop(f"edit_description_{task_id}", None)
    return True


def get_filtered_tasks(filter_name: str) -> list[dict[str, Any]]:
    """Return tasks matching All, Active, or Completed."""
    init_state()
    tasks = st.session_state.tasks
    if filter_name == "Active":
        return [task for task in tasks if not task["completed"]]
    if filter_name == "Completed":
        return [task for task in tasks if task["completed"]]
    return list(tasks)


def _set_notice(kind: str, message: str) -> None:
    st.session_state.notice = (kind, message)


def _start_edit(task_id: int) -> None:
    for task in st.session_state.tasks:
        if task["id"] == task_id:
            st.session_state.editing_id = task_id
            st.session_state[f"edit_title_{task_id}"] = task["title"]
            st.session_state[f"edit_description_{task_id}"] = task[
                "description"
            ]
            return


def _save_edit(task_id: int) -> None:
    title = st.session_state.get(f"edit_title_{task_id}", "")
    description = st.session_state.get(f"edit_description_{task_id}", "")
    if not title.strip():
        _set_notice("error", "Task title is required.")
        return

    if update_task(task_id, title, description):
        st.session_state.editing_id = None
        st.session_state.pop(f"edit_title_{task_id}", None)
        st.session_state.pop(f"edit_description_{task_id}", None)
        _set_notice("success", "Task updated.")
    else:
        st.session_state.editing_id = None
        _set_notice("error", "That task could not be found.")


def _cancel_edit(task_id: int) -> None:
    st.session_state.editing_id = None
    st.session_state.pop(f"edit_title_{task_id}", None)
    st.session_state.pop(f"edit_description_{task_id}", None)


def _toggle_with_notice(task_id: int) -> None:
    if toggle_task(task_id):
        task = next(task for task in st.session_state.tasks if task["id"] == task_id)
        message = "Task completed." if task["completed"] else "Task marked active."
        _set_notice("success", message)


def _confirm_delete(task_id: int) -> None:
    if delete_task(task_id):
        _set_notice("success", "Task deleted.")
    else:
        _set_notice("error", "That task could not be found.")


def _cancel_delete() -> None:
    st.session_state.confirm_delete_id = None


def main() -> None:
    st.set_page_config(page_title="To-Do List", page_icon="✅", layout="centered")
    init_state()

    st.title("To-Do List")
    notice = st.session_state.pop("notice", None)
    if notice:
        kind, message = notice
        if kind == "error":
            st.error(message)
        else:
            st.success(message)

    total = len(st.session_state.tasks)
    completed = sum(task["completed"] for task in st.session_state.tasks)
    active = total - completed
    metric_columns = st.columns(3)
    metric_columns[0].metric("Total", total)
    metric_columns[1].metric("Active", active)
    metric_columns[2].metric("Completed", completed)

    st.subheader("Add a task")
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Title", key="new_title")
        description = st.text_area("Description (optional)", key="new_description")
        submitted = st.form_submit_button(
            "Add task", type="primary", key="add_task_submit"
        )
    if submitted:
        if add_task(title, description):
            st.success("Task added.")
        else:
            st.error("Task title is required.")

    st.subheader("Your tasks")
    filter_name = st.radio(
        "Filter tasks",
        options=("All", "Active", "Completed"),
        horizontal=True,
        label_visibility="collapsed",
        key="task_filter",
    )
    tasks = get_filtered_tasks(filter_name)
    if not tasks:
        st.info("No tasks in this view yet.")

    for task in tasks:
        task_id = task["id"]
        with st.container(border=True):
            if task["completed"]:
                st.markdown(f"~~{task['title']}~~ ✅")
            else:
                st.markdown(f"**{task['title']}**")
            if task["description"]:
                st.text(task["description"])
            st.caption(f"Created {task['created_at']}")

            action_columns = st.columns(3)
            action_columns[0].button(
                "Undo" if task["completed"] else "Done",
                key=f"toggle_task_{task_id}",
                on_click=_toggle_with_notice,
                args=(task_id,),
                use_container_width=True,
            )
            action_columns[1].button(
                "Edit",
                key=f"edit_task_{task_id}",
                on_click=_start_edit,
                args=(task_id,),
                use_container_width=True,
            )
            action_columns[2].button(
                "Delete",
                key=f"delete_task_{task_id}",
                on_click=lambda task_id=task_id: setattr(
                    st.session_state, "confirm_delete_id", task_id
                ),
                use_container_width=True,
            )

            if st.session_state.editing_id == task_id:
                with st.form(f"edit_form_{task_id}"):
                    st.text_input("Title", key=f"edit_title_{task_id}")
                    st.text_area(
                        "Description (optional)",
                        key=f"edit_description_{task_id}",
                    )
                    save_column, cancel_column = st.columns(2)
                    save_column.form_submit_button(
                        "Save",
                        type="primary",
                        key=f"save_edit_{task_id}",
                        on_click=_save_edit,
                        args=(task_id,),
                    )
                    cancel_column.form_submit_button(
                        "Cancel",
                        key=f"cancel_edit_{task_id}",
                        on_click=_cancel_edit,
                        args=(task_id,),
                    )

            if st.session_state.confirm_delete_id == task_id:
                st.warning("Are you sure you want to delete this task?")
                confirm_column, cancel_column = st.columns(2)
                confirm_column.button(
                    "Confirm",
                    key=f"confirm_delete_{task_id}",
                    on_click=_confirm_delete,
                    args=(task_id,),
                    type="primary",
                )
                cancel_column.button(
                    "Cancel",
                    key=f"cancel_delete_{task_id}",
                    on_click=_cancel_delete,
                )


if __name__ == "__main__":
    main()