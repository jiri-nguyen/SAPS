/** Full-page navigation, replaceable in tests (jsdom cannot navigate). */
export const browser = {
  assign(url: string): void {
    window.location.assign(url);
  },
};
