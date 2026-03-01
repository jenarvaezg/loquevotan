import { describe, it, expect } from 'vitest';
import { getLeg, fmt, normalize, pct, avatarInitials, resultMarginText, dipPhotoUrl, subTipoLabel, subTipoBadgeClass, affinityColor, votoPillClass, getGroupInfo } from '../../src/utils.js';

describe('utils.js', () => {
  describe('getLeg', () => {
    it('returns correct legislatura for date', () => {
      expect(getLeg('2024-01-01')).toBe('XV');
      expect(getLeg('2021-05-10')).toBe('XIV');
      expect(getLeg('2018-01-01')).toBe('XII');
    });

    it('returns empty string if out of bounds', () => {
      expect(getLeg('1990-01-01')).toBe('');
    });
  });

  describe('fmt', () => {
    it('replaces underscores with spaces', () => {
      expect(fmt('hello_world')).toBe('hello world');
      expect(fmt('')).toBe('');
      expect(fmt(null)).toBe('');
    });
  });

  describe('normalize', () => {
    it('normalizes string, removes accents and lowercases', () => {
      expect(normalize('Héllo Wórld')).toBe('hello world');
      expect(normalize('ESPAÑA')).toBe('espana');
    });

    it('handles falsy values', () => {
      expect(normalize(null)).toBe('');
      expect(normalize(undefined)).toBe('');
      expect(normalize('')).toBe('');
    });
  });

  describe('pct', () => {
    it('formats number to percentage string with one decimal', () => {
      expect(pct(0.5)).toBe('50.0%');
      expect(pct(0.333333)).toBe('33.3%');
      expect(pct(1)).toBe('100.0%');
    });
  });

  describe('avatarInitials', () => {
    it('extracts initials from name format "Apellidos, Nombre"', () => {
      expect(avatarInitials('Pérez García, Juan')).toBe('JP');
      expect(avatarInitials('Sánchez, Pedro')).toBe('PS');
    });

    it('handles names without comma', () => {
      expect(avatarInitials('Juan Pérez')).toBe('J'); // 'Juan Pérez' -> apellido='Juan Pérez', nombre='' -> '' + 'J'
    });
  });

  describe('resultMarginText', () => {
    it('formats margin text correctly', () => {
      expect(resultMarginText({ result: 'Aprobada', margin: 10 })).toBe('Aprobada por 10 votos');
      expect(resultMarginText({ result: 'Rechazada', margin: 5 })).toBe('Rechazada por 5 votos');
      expect(resultMarginText({ result: 'Empate' })).toBe('Empate');
    });
  });

  describe('dipPhotoUrl', () => {
    it('returns string if string is provided', () => {
      expect(dipPhotoUrl('http://example.com/photo.jpg')).toBe('http://example.com/photo.jpg');
    });

    it('returns null if no entry', () => {
      expect(dipPhotoUrl(null)).toBeNull();
      expect(dipPhotoUrl({})).toBeNull();
    });

    it('returns proper congreso URL for highest legislatura', () => {
      expect(dipPhotoUrl({ 'XIV': '123', 'XV': '456' })).toBe('https://www.congreso.es/docu/imgweb/diputados/456_15.jpg');
    });
  });

  describe('subTipoLabel', () => {
    it('returns translated label', () => {
      expect(subTipoLabel('totalidad')).toBe('Enmienda a la totalidad');
      expect(subTipoLabel('unknown')).toBe('unknown');
    });
  });

  describe('subTipoBadgeClass', () => {
    it('returns correct class', () => {
      expect(subTipoBadgeClass('final')).toBe('badge--final');
      expect(subTipoBadgeClass('totalidad')).toBe('badge--totalidad');
      expect(subTipoBadgeClass('transaccional')).toBe('badge--transaccional');
      expect(subTipoBadgeClass('other')).toBe('badge--enmienda');
    });
  });

  describe('affinityColor', () => {
    it('returns correct color based on percentage', () => {
      expect(affinityColor(0.9)).toBe('#16a34a');
      expect(affinityColor(0.7)).toBe('#86efac');
      expect(affinityColor(0.5)).toBe('#fde047');
      expect(affinityColor(0.3)).toBe('#fca5a5');
      expect(affinityColor(0.1)).toBe('#dc2626');
    });
  });

  describe('votoPillClass', () => {
    it('returns class for vote code', () => {
      expect(votoPillClass(1)).toBe('voto-pill--favor');
      expect(votoPillClass(2)).toBe('voto-pill--contra');
      expect(votoPillClass(3)).toBe('voto-pill--abstencion');
    });
  });

  describe('getGroupInfo', () => {
    it('returns correct info for exact match', () => {
      const info = getGroupInfo('GS');
      expect(info.label).toBe('PSOE');
      expect(info.color).toBe('#ef1c27');
    });

    it('returns fallback info based on contains', () => {
      const info = getGroupInfo('Grupo Parlamentario Socialista');
      expect(info.label).toBe('PSOE');
      expect(info.color).toBe('#ef1c27');
    });

    it('returns generic info if no match', () => {
      const info = getGroupInfo('Unknown Group');
      expect(info.label).toBe('Unknown Group');
      expect(info.color).toBe('#64748b');
    });
  });
});
