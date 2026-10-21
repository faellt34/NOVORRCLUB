import { saveQr } from './saveQr';

beforeEach(() => {
  jest.useFakeTimers();
  URL.createObjectURL = jest.fn().mockReturnValueOnce('blob:svg').mockReturnValue('blob:png');
  URL.revokeObjectURL = jest.fn();
  window.Image = class { set src(value) { this.onload(); } };
  HTMLCanvasElement.prototype.getContext = jest.fn(() => ({ fillRect: jest.fn(), drawImage: jest.fn() }));
  HTMLCanvasElement.prototype.toBlob = jest.fn(callback => callback(new Blob(['png'], { type: 'image/png' })));
  navigator.canShare = jest.fn(() => false);
  navigator.share = jest.fn();
});
afterEach(() => { jest.runOnlyPendingTimers(); jest.useRealTimers(); jest.restoreAllMocks(); });

test('missing QR fails instead of reporting a successful save', async () => {
  await expect(saveQr(null, 'qr.png')).rejects.toThrow('ainda não está disponível');
  expect(navigator.share).not.toHaveBeenCalled();
});

test('download creates a PNG link attached to the document, then cleans up', async () => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const click = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
    expect(document.body.contains(this)).toBe(true);
    expect(this.download).toBe('qr-p5-TEST.png');
    expect(this.href).toBe('blob:png');
  });
  await expect(saveQr(svg, 'qr-p5-TEST.png')).resolves.toBe('download');
  expect(click).toHaveBeenCalledTimes(1);
  expect(HTMLCanvasElement.prototype.toBlob).toHaveBeenCalled();
});

test('cancelled mobile share does not trigger a second download', async () => {
  navigator.canShare.mockReturnValue(true);
  navigator.share.mockRejectedValue(Object.assign(new Error('cancel'), { name: 'AbortError' }));
  const click = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  await expect(saveQr(document.createElementNS('http://www.w3.org/2000/svg', 'svg'), 'qr.png')).resolves.toBe('cancelled');
  expect(click).not.toHaveBeenCalled();
});
