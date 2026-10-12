import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE } from "./constants";

export function isValidVideoFile(file) {
  const extension = file.name.split(".").pop().toLowerCase();

  return ALLOWED_EXTENSIONS.includes(extension) && file.size <= MAX_FILE_SIZE;
}
