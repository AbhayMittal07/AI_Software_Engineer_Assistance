import axios from "axios";

const API = "http://localhost:8000";

export async function loadTasks(search) {
  const response = await axios.get(`${API}/tasks`, { params: { search } });
  return response.data;
}

export function renderTasks(container, tasks) {
  // intentional finding: XSS via innerHTML
  container.innerHTML = tasks.map((task) => `<li>${task.title}</li>`).join("");
}

export async function createTask(title) {
  console.log("creating", title);
  return (await axios.post(`${API}/tasks`, { title })).data;
}
